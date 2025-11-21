import re
import traceback
from typing import Callable, List
import dotenv
import keyboard

from pcm_processor import PcmProcessor
import pcm_utils
import silerovad
import subtitles
dotenv.load_dotenv()
import os, json, base64, threading, queue, time
import numpy as np
import sounddevice as sd
from websocket import WebSocketApp

API_KEY = os.environ.get("OPENAI_API_KEY", "")
assert API_KEY, "Set OPENAI_API_KEY in your environment."

class Query:
    def __init__(self):
        self.start_time = time.time()
        self.query_text = ""
        self.response_text = ""
        self.done = False
        self.duration = 0
    def __str__(self):
        return str(self.__dict__)



    
class Oai:
    STATE_IDLE = "IDLE"
    STATE_SENDING_SPEECH = "SENDING_SPEECH"
    STATE_RECEIVING_RESPONSE = "RECEIVING_RESPONSE"

    def __init__(self, 
                 system_prompt = "", 
                 language = "sv", 
                 voice="sage", 
                 temperature = 0.8,
                 query_update_callback: Callable[[Query], None] = None,
                 state_callback: Callable[[str], None] = None,
                 response_audio_callback: Callable[[int, int, np.ndarray], None] = None,
                 intermediate_response_text_callback: Callable[[str], None] = None
                ):
        def on_pcm16_frames(sample_rate:int, channel_cnt:int, frames:np.ndarray):
            self._set_state(self.STATE_SENDING_SPEECH)
            for chunk in self.pcm_processor.get_frame_chunks(sample_rate, channel_cnt, frames):
                self._send_data({
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(bytes(chunk.tobytes())).decode("ascii"),
                })

        def on_speech_end(sample_rate:int, channel_cnt:int, pcm16_chunks:List[np.ndarray]):
            self._set_state(self.STATE_RECEIVING_RESPONSE)
            self._send_data({
                "type": "response.create",
                "response": {
                    "temperature": temperature,
                }
            })

        self.pcm_processor = PcmProcessor(24000, 1, millis_per_chunk=100) # Realtime API expects PCM16 mono ~24 kHz
        self._sending_speech = False
        self.silero = silerovad.SileroVad(
            threshold=.35,
            head_millis=1000,
            speech_stream_callback=on_pcm16_frames,
            speech_end_callback=on_speech_end
        )
        self.state_callback = state_callback
        self.query_response_callback = query_update_callback
        self.response_audio_callback = response_audio_callback
        self.intermediate_response_text_callback = intermediate_response_text_callback
        self.language = language
        self.voice = voice
        self.system_prompt = system_prompt
        self._cur_query = Query()
        self._listening = True
        self._state = self.STATE_IDLE
        self.start()
    @property
    def state(self):
        return self._state
    
    def _set_state(self, state):
        if self._state != state:
            if state == self.STATE_SENDING_SPEECH:
                self.cancel_current()
                self._cur_query = Query()
            self._state = state
            if self.state_callback:
                self.state_callback(state)
    def start(self):
        def on_open(ws):
            print("WebSocket connected")
            session_data = {
                "instructions": self.system_prompt,
                "turn_detection": {
                    "type": "server_vad",
                    "create_response": False # We decide ourselves when it's time for response
                },
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "gpt-4o-mini-transcribe",   # or gpt-4o-transcribe / whisper-1
                    "language": self.language
                } ,
                "modalities": ["text", "audio"] if self.voice else ["text"],                      
            }
            if self.voice:
                session_data["voice"] = self.voice

            self._send_data({
                "type": "session.update",
                "session": session_data,
            })

        def on_error(ws, error):
            print("WebSocket error:", error)

        def on_close(ws, code, msg):
            print("WebSocket closed:", code, msg)


        def on_message(ws, message):
            try:
                evt = json.loads(message)
                t = evt.get("type", "")
                #print(t)
                if t == "error":
                    if error := evt.get("error"):
                        if error.get("code") == "response_cancel_not_active":
                            return
                    print("ERROR:", evt)
                elif t == "response.audio.delta":
                    b = base64.b64decode(evt.get("delta", ""))
                    if self.response_audio_callback:
                        frames = np.frombuffer(b, dtype=np.int16)
                        self.response_audio_callback(24000, 1, frames)
                elif t == "conversation.item.input_audio_transcription.delta":
                    self._cur_query.query_text += evt.get("delta")
                elif t == "conversation.item.input_audio_transcription.completed":
                    self._cur_query.query_text += " "
                    #print("USER:", evt.get("transcript"), evt)
                elif t in ("response.audio_transcript.delta", "response.text.delta"):
                    text = evt.get("delta")
                    self._cur_query.response_text += text
                    if self.query_response_callback:
                        self.query_response_callback(self._cur_query)
                    if self.intermediate_response_text_callback:
                        self.intermediate_response_text_callback(text)
                # elif delta := evt.get("delta"):
                #     print(t,delta)
                elif t == "response.done":
                    if evt["response"]["status"] == "completed":
                        self._cur_query.done = True
                        self._cur_query.duration = time.time() - self._cur_query.start_time
                    if self.query_response_callback:
                        self.query_response_callback(self._cur_query)
                    self._set_state(self.STATE_IDLE)
                else:
                    pass
                    #print(t, (time.time() - self._cur_query.start_time))
                    
            except Exception:
                traceback.print_exc()
                print(evt)

        self.ws = WebSocketApp(
            "wss://api.openai.com/v1/realtime?model=gpt-realtime",
            header=[
                "Authorization: Bearer " + API_KEY,
                "OpenAI-Beta: realtime=v1",
            ],
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        threading.Thread(target=self.ws.run_forever, daemon=True).start()        
    def __del__(self):
        try:
            self.ws.close()
        except:
            pass

    def _send_data(self, data:dict):
        self.ws.send(json.dumps(data))

    def push_pcm16_frames(self, sample_rate:int, channel_cnt:int, frames:np.ndarray):
        if self._listening:
            self.silero.push_pcm16_frames(sample_rate, channel_cnt, frames)
    
    def set_listening(self, listening):
        if self._listening != listening:
            print("listening:",listening)
            self._listening = listening
    
    def cancel_current(self):
        self._send_data({"type": "response.cancel"})

import comm
class PepperSim:
    def __init__(self):
        self.audio_player = pcm_utils.AsyncAudioPlayer(16000)
        self.state_reporter = comm.RobotStateReporter()
        
        def loop():
            while True:
                head_touched = keyboard.is_pressed('h')
                if head_touched:
                    self.audio_player.clear_queue()
                self.state_reporter.report_talking(self.audio_player.is_playing())
                self.state_reporter.report_head_touched(head_touched)
                time.sleep(.1)
        threading.Thread(target=loop, daemon=True).start()

    def push_pcm16_frames(self, sample_rate:int, channel_cnt:int, frames:np.ndarray):
        self.audio_player.push_pcm16_frames(sample_rate, channel_cnt, frames)

def split_keep(text):
    parts = re.split(r'([,.?!])', text)
    out = []
    for i in range(0, len(parts)-1, 2):
        out.append(parts[i] + parts[i+1])
    return out

class SubtitleManager:
    def __init__(self, signal_threshold=500, silence_duration_threshold=.2):
        self.signal_threshold = signal_threshold
        self.duration_threshold = silence_duration_threshold
        self._consecutive_silent_sample_cnt = 0
        self.silence_timestamps = []
        self._sample_cnt = 0
        self._sample_rate = -1
        self._full_text = ""
        self.sent_text = ""
        self._last_pcm_time = 0
        self._start_time = 0
        self._text_chunks:List[str] = []
        self._cur_subtitle = ""
        def loop():
            while True:
                now = time.time()
                if self._sample_cnt > 0:
                    speech_dur = self._sample_cnt / self._sample_rate
                    play_time = now - self._start_time
                    remaining_time = speech_dur - play_time
                    speech_input_done = time.time() - self._last_pcm_time > .5
                    #print("speech_dur:",speech_dur, " play_time:", round(play_time,1), " remaining_time:", remaining_time)
                    if speech_input_done and remaining_time < -3:
                        self.reset()
                    elif speech_input_done and remaining_time <= 0:
                        self._set_subtitle(self._full_text)
                    else:
                        send_chunk_cnt = 1 + len([s for s in self.silence_timestamps if s < play_time])
                        if send_chunk_cnt <= len(self._text_chunks):
                            self._set_subtitle("".join(self._text_chunks[:send_chunk_cnt]))
                        #print("chunk_cnt:", len(self._text_chunks), " send_cnt:", send_chunk_cnt, " play_time:", round(play_time,1), "ts:",[round(ts,1) for ts in self.silence_timestamps] ," _text_chunks", self._text_chunks)
                time.sleep(.2)
        threading.Thread(target=loop, daemon=True).start()

    def _set_subtitle(self, text):
        if text != self._cur_subtitle:
            print(text)
            self._cur_subtitle = text
            subtitles.set_text(text)
    def reset(self):
        if self._sample_cnt > 0:
            print("reset:", self.silence_timestamps)
            self._full_text = ""
            self.silence_timestamps = []
            self._sample_cnt = 0
            subtitles.set_text("")
   

    def push_text(self, text:str):
        self._full_text += text
        self._text_chunks = split_keep(self._full_text)
        # print(
        #     self._full_text.rjust(100), 
        #     self._text_chunks
        # )
    def push_pcm16_frames(self, sample_rate:int, channel_cnt:int, frames:np.ndarray):
        if channel_cnt > 1:
            return False
        self._last_pcm_time = time.time()
        self._sample_rate = sample_rate
        if self._sample_cnt == 0:
            self._start_time = time.time()
        abs_amplitudes = np.abs(frames)
        silent_sample_cnt_threshold = int(sample_rate * self.duration_threshold)
        for amp in abs_amplitudes:
            self._sample_cnt += 1
            if amp < self.signal_threshold:
                self._consecutive_silent_sample_cnt += 1
            else:
                if self._consecutive_silent_sample_cnt >= silent_sample_cnt_threshold:
                    self.silence_timestamps.append(self._sample_cnt / sample_rate)
                    print(self.silence_timestamps)
                self._consecutive_silent_sample_cnt = 0

def main():
    subtitles.start_server()
    pepper = PepperSim()
    def on_robot_state_change(state:comm.RobotState):
        print(state)
        if state.head_touched:
            oai.cancel_current()
    robot_state_listener = comm.RobotStateListener(on_robot_state_change)
    
    def on_query_update(query:Query):
        if query.done:
            print(query)

    subtitle_manager = SubtitleManager()
    def on_response_audio(sample_rate:int, channel_cnt:int, frames:np.ndarray):
        pepper.push_pcm16_frames(sample_rate, channel_cnt, frames)
        subtitle_manager.push_pcm16_frames(sample_rate, channel_cnt, frames)

    oai = Oai(
        system_prompt=(
            "Du är roboten Pepper."
            "Du är glad och artig."
            "Du pratar svenska. Långsamt, tydligt och kortfattat."
        ),
        #voice=None,
        query_update_callback = on_query_update,
        response_audio_callback = on_response_audio,
        state_callback=print,
        intermediate_response_text_callback=subtitle_manager.push_text
    )
    def muter():
        while True:
            oai.set_listening(oai.state != oai.STATE_RECEIVING_RESPONSE and not robot_state_listener.state.talking)
            time.sleep(.1)
    threading.Thread(target=muter, daemon=True).start()
    pcm_utils.listen_on_local_mic(48000,[oai.push_pcm16_frames], channel_cnt=1)

if __name__ == "__main__":

    # text = "Javisst, jag hjälper dig gärna. Vad är det du skulle vilja ha just nu? Något att veta, något att göra, eller kanske något helt annat? Jag anpassar mig efter dina behov."
    # silences = [1.011, 3.3080416666666665, 6.210458333333333, 7.802833333333333, 9.612041666666666, 12.193333333333333]
    # text_chunks = split_keep(text)
    # titr = iter(text_chunks)
    # tsil = iter(silences)
    # start = time.time()
    # print(next(titr))
    # for t in silences:
    #     while time.time() - start < t:
    #         time.sleep(.01)
    #     print(next(titr))
        

    # print(len(text_chunks), len(silences))
    main()

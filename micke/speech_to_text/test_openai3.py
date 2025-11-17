import traceback
from typing import Callable, List
import dotenv
import keyboard

from pcm_processor import PcmProcessor
import pcm_utils
import silerovad
dotenv.load_dotenv()
import os, json, base64, threading, queue, time
import numpy as np
import sounddevice as sd
from websocket import WebSocketApp

API_KEY = os.environ.get("OPENAI_API_KEY", "")
assert API_KEY, "Set OPENAI_API_KEY in your environment."

class QueryResponse:
    def __init__(self):
        self.query_text = ""
        self.response_text = ""
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
                 query_response_callback: Callable[[QueryResponse], None] = None,
                 state_callback: Callable[[str], None] = None,
                 response_audio_callback: Callable[[int, int, np.ndarray], None] = None
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
        self.query_response_callback = query_response_callback
        self.response_audio_callback = response_audio_callback
        self.language = language
        self.voice = voice
        self.system_prompt = system_prompt
        self._cur_response = QueryResponse()
        self._listening = True
        self._state = self.STATE_IDLE
        self.start()
    @property
    def state(self):
        return self._state
    
    def _set_state(self, state):
        if self.state_callback and self._state != state:
            self.state_callback(state)
        self._state = state
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
                    print("ERROR:", evt)
                elif t == "response.audio.delta":
                    b = base64.b64decode(evt.get("delta", ""))
                    if self.response_audio_callback:
                        self.response_audio_callback(24000, 1, np.frombuffer(b, dtype=np.int16))
                elif t == "conversation.item.input_audio_transcription.completed":
                    self._cur_response.query_text = evt.get("transcript")
                    #print("USER:", evt.get("transcript"))
                elif t == "response.done":
                    if evt["response"]["status"] == "completed":
                        content = evt["response"]["output"][0]["content"][0]
                        text = content.get("text", content.get("transcript", "RESPONSE_CONTENT_ERROR"))
                        self._cur_response.response_text = text
                    self._set_state(self.STATE_IDLE)
                        #print("RESPTEXT:",text)
                # elif t == "response.audio.done":
                #     print(t)

                if t.endswith(".completed") or t.endswith(".done"):
                    if self._cur_response.query_text and self._cur_response.response_text:
                        if self.query_response_callback:
                            self.query_response_callback(self._cur_response)
                        self._cur_response = QueryResponse()
                        
                    
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


def main():
    pepper = PepperSim()
    def on_robot_state_change(state:comm.RobotState):
        print(state)
        if state.head_touched:
            oai.cancel_current()
    robot_state_listener = comm.RobotStateListener(on_robot_state_change)
    oai = Oai(
        system_prompt=(
            "Du är roboten Pepper."
            "Du är glad och artig."
            "Du pratar svenska. Långsamt, tydligt och kortfattat."
        ),
        query_response_callback = print,
        response_audio_callback = pepper.push_pcm16_frames,
        state_callback=print
    )
    def muter():
        while True:
            oai.set_listening(oai.state != oai.STATE_RECEIVING_RESPONSE and not robot_state_listener.state.talking)
            time.sleep(.1)
    threading.Thread(target=muter, daemon=True).start()
    pcm_utils.listen_on_local_mic(48000,[oai.push_pcm16_frames], channel_cnt=1)
if __name__ == "__main__":
    main()

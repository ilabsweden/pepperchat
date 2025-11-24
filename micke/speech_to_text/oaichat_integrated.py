import traceback
from typing import Callable, List, Tuple
import dotenv
import __parentdir
import silerovad
from pcm_processor import PcmProcessor
dotenv.load_dotenv()
import os, json, base64, threading, time
import numpy as np
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

    
class OaiChatIntegrated:
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
                    # OBS! ERROR: {'type': 'error', 'event_id': 'event_Cf56YfnjwVCABifRNL02D', 'error': {'type': 'invalid_request_error', 'code': 'session_expired', 'message': 'Your session hit the maximum duration of 60 minutes.', 'param': None, 'event_id': None}}
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


import traceback
from typing import Callable, List
import dotenv

from pcm_processor import PcmProcessor
import pcm_utils
import silerovad
dotenv.load_dotenv()
import os, json, base64, threading, queue, time
import numpy as np
import sounddevice as sd
from websocket import WebSocketApp

# ----- Config -----
API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-realtime"          # or: gpt-4o-realtime-preview, gpt-realtime-mini
SAMPLE_RATE = 24000             # Realtime API expects PCM16 mono ~24 kHz
VOICE = "sage"                 # alloy, verse, coral, etc.
INSTRUCTIONS = (
    "Du är roboten Pepper."
    "Du är glad och artig."
    "Du pratar svenska. Långsamt, tydligt och kortfattat."
)
# -------------------

USE_SILERO = True

assert API_KEY, "Set OPENAI_API_KEY in your environment."

WS_URL = f"wss://api.openai.com/v1/realtime?model={MODEL}"


class QueryResponse:
    def __init__(self):
        self.query_text = ""
        self.response_text = ""
    def to_string(self):
        return str(self.__dict__)
    
class Oai:
        
    def __init__(self):
        def on_pcm16_frames(sample_rate:int, channel_cnt:int, frames:np.ndarray):
            for chunk in self.pcm_processor.get_frame_chunks(sample_rate, channel_cnt, frames):
                evt = {
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(bytes(chunk.tobytes())).decode("ascii"),
                }
                self.ws.send(json.dumps(evt))

        def on_speech_end(sample_rate:int, channel_cnt:int, pcm16_chunks:List[np.ndarray]):
            resp = {
                "type": "response.create",
                "response": {
                    "temperature": 0.8,
                    #"max_output_tokens": 50,
                    # Optional: per-turn instructions/system biasing
                    #"instructions": INSTRUCTIONS + " Svara kortfattat."
                }
            }
            self.ws.send(json.dumps(resp))

        self.pcm_processor = PcmProcessor(SAMPLE_RATE, 1, millis_per_chunk=100)
        self.silero = silerovad.SileroVad(
            threshold=.35,
            head_millis=1000,
            speech_stream_callback=on_pcm16_frames,
            speech_end_callback=on_speech_end
        )
        self.response_callback: Callable[[QueryResponse], None] = None
        self.audio_callback: Callable[[bytes], None] = None
        self.voice = VOICE
        self._cur_response = QueryResponse()
        self._response_audio_buffer = bytearray()

    def start(self):
        def on_open(ws):
            print("WebSocket connected")
            session_data = {
                "instructions": INSTRUCTIONS,
                "turn_detection": {
                    "type": "server_vad",
                    "create_response": False # We decide ourselves when it's time for response
                },
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "gpt-4o-mini-transcribe",   # or gpt-4o-transcribe / whisper-1
                    "language": "sv"
                } ,
                "modalities": ["text", "audio"] if self.voice else ["text"],                      
            }
            if self.voice:
                session_data["voice"] = self.voice

            session_update = {
                "type": "session.update",
                "session": session_data,
            }

            ws.send(json.dumps(session_update))

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
                    if self.audio_callback:
                        self.audio_callback(b)
                elif t == "conversation.item.input_audio_transcription.completed":
                    self._cur_response.query_text = evt.get("transcript")
                    print("USER:", evt.get("transcript"))
                elif t == "response.done":
                    if evt["response"]["status"] == "completed":
                        content = evt["response"]["output"][0]["content"][0]
                        text = content.get("text", content.get("transcript", "RESPONSE_CONTENT_ERROR"))
                        self._cur_response.response_text = text
                        print("RESPTEXT:",text)
                # elif t == "response.audio.done":
                #     print(t)

                if t.endswith(".completed") or t.endswith(".done"):
                    if self._cur_response.query_text and self._cur_response.response_text:
                        if self.response_callback:
                            self.response_callback(self._cur_response)
                        self._cur_response = QueryResponse()
                    
            except Exception:
                traceback.print_exc()
                print(evt)

        self.ws = WebSocketApp(
            WS_URL,
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

    def push_pcm16_frames(self, sample_rate:int, channel_cnt:int, frames:np.ndarray):
        self.silero.push_pcm16_frames(sample_rate, channel_cnt, frames)



    

def main():
    play_queue: "queue.Queue[bytes]" = queue.Queue()
    running = True
    def audio_player():
        with sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as out:
            while running:
                chunk = play_queue.get()
                out.write(chunk)
    threading.Thread(target=audio_player, daemon=True).start()                
    
    oai = Oai()
    oai.voice = None
    oai.start()
    def on_response(response:QueryResponse):
        print(response.to_string())
    def on_response_audio(data:bytes):
        play_queue.put(data)

    oai.response_callback = on_response
    oai.audio_callback = on_response_audio
    silerovad.SileroVad.PRINT_DEBUG = True
    pcm_utils.listen_on_local_mic(48000,[oai.push_pcm16_frames], channel_cnt=1)
    oai.ws.close()
    running = False
if __name__ == "__main__":
    main()
    med_audio = {'type': 'response.done', 'event_id': 'event_CboCU20qDEylLj8slTfRK', 'response': {'object': 'realtime.response', 'id': 'resp_CboCTudL9dqu8i75rhbwK', 'status': 'completed', 'status_details': None, 'output': [{'id': 'item_CboCT1h5xb7DG8jp5BLLm', 'object': 'realtime.item', 'type': 'message', 'status': 'completed', 'role': 'assistant', 'content': [{'type': 'audio', 'transcript': 'God morgon! Hur är läget med dig idag?'}]}], 'conversation_id': 'conv_CboCPuWpw58bqle1kEGzn', 'modalities': ['text', 'audio'], 'voice': 'alloy', 'output_audio_format': 'pcm16', 'temperature': 0.8, 'max_output_tokens': 'inf', 'usage': {'total_tokens': 122, 'input_tokens': 34, 'output_tokens': 88, 'input_token_details': {'text_tokens': 26, 'audio_tokens': 8, 'image_tokens': 0, 'cached_tokens': 0, 'cached_tokens_details': {'text_tokens': 0, 'audio_tokens': 0, 'image_tokens': 0}}, 'output_token_details': {'text_tokens': 22, 'audio_tokens': 66}}, 'metadata': None}}
    utan = {'type': 'response.done', 'event_id': 'event_CboGD3Sb25wcTySRJK0qw', 'response': {'object': 'realtime.response', 'id': 'resp_CboGCntUtZx2GrfOuUa0E', 'status': 'completed', 'status_details': None, 'output': [{'id': 'item_CboGCABi1Ifa7KI1aLCW7', 'object': 'realtime.item', 'type': 'message', 'status': 'completed', 'role': 'assistant', 'content': [{'type': 'text', 'text': 'God morgon! Hur kan jag hjälpa dig idag?'}]}], 'conversation_id': 'conv_CboG75Icyv3Brg5cmbMB3', 'modalities': ['text'], 'voice': 'alloy', 'output_audio_format': 'pcm16', 'temperature': 0.8, 'max_output_tokens': 'inf', 'usage': {'total_tokens': 50, 'input_tokens': 37, 'output_tokens': 13, 'input_token_details': {'text_tokens': 26, 'audio_tokens': 11, 'image_tokens': 0, 'cached_tokens': 0, 'cached_tokens_details': {'text_tokens': 0, 'audio_tokens': 0, 'image_tokens': 0}}, 'output_token_details': {'text_tokens': 13, 'audio_tokens': 0}}, 'metadata': None}}
    #print(utan["response"]["output"][0]["content"][0])
    #print (json.dumps(med_audio, indent=4))

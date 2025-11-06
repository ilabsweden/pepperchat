from dataclasses import dataclass
import os
import sys
import json
import queue
import threading
import time
import traceback
import numpy as np
from websockets.sync.client import connect  # installed with deepgram-sdk dependencies
import pcm_utils
import urllib.parse

from transcriber import Transcriber, Transcript, TranscriberResult, TranscriptWord
from transcript_comm import TranscriptSender

import dotenv
dotenv.load_dotenv()

@dataclass
class DeepgramConfig:
    language:str = "sv-SE"
    model:str = "nova-3"
    encoding:str = "linear16"
    sample_rate:int = 16000 # Nova 3 is trained on 16kHz mono, so let's stick to that
    channels:int = 1
    smart_format:bool = True
    interim_results:bool = True
    vad_events:bool = True


class DeepgramTranscriber(Transcriber):
    PRINT_DEBUG = False
    def debug_print(self, *args, **kwargs):
        if self.PRINT_DEBUG:
            print(f"{self.__class__.__name__}:", *args, **kwargs)
    def __init__(self):
        Transcriber.__init__(self)
        self._audio_q: queue.Queue[bytes] = queue.Queue()
        self._api_key = os.getenv("DEEPGRAM_API_KEY")
        self._running = threading.Event()
        self.config = DeepgramConfig(language = "sv-SE")
        self.pcm_processor = pcm_utils.PcmProcessor(16000, 1, frames_per_chunk=320)
        self.start()

    def push_pcm16_frames(self, sample_rate:int, channel_cnt:int, frames:np.ndarray):
        for chunk in self.pcm_processor.get_frame_chunks(sample_rate, channel_cnt, frames):
            self._audio_q.put(chunk.tobytes())

    def parse_response(self, data:dict):
        response_type = data.get("type")
        if response_type == "Results":
            speech_final, is_final, from_finalize = [bool(data.get(key)) for key in ["is_final", "speech_final", "from_finalize"]]
            if channel := data.get("channel", {}):
                transcripts = [
                    Transcript(
                        transcript=alt.get("transcript", ""),
                        confidence=alt.get("confidence", -1),
                        words=[TranscriptWord(word.get("word"), word.get("confidence")) for word in alt.get("words",[])]
                    ) for alt in channel.get("alternatives", []) if alt.get("transcript", "")
                ]
                if transcripts:
                    self._on_transcribed(transcripts, is_final, channel)
            if speech_final:
                self.debug_print("speech_final")

        elif response_type == "Error":
            print(f"\n[Deepgram error] {data.get('message')}", file=sys.stderr)
        else:
            self.debug_print(response_type)
        
    def __del__(self):
        try:
            self.stop()
        except:
            pass
        
    def stop(self):
        self._running.clear()

    def start(self):
        def work():
            headers = {"Authorization": f"Token {self._api_key}"}
            self._running.set()
            # Open the WebSocket
            url = f"wss://api.deepgram.com/v1/listen?{urllib.parse.urlencode(self.config.__dict__).replace('True','true')}"
            with connect(url, additional_headers=headers) as ws:
                
                # Send audio data available in the queue
                def send_loop():
                    last_keepalive = 0.0
                    while self._running.is_set():
                        # KeepAlive every 4s to prevent NET timeouts during silence
                        now = time.time()
                        if now - last_keepalive > 4.0:
                            try:
                                ws.send(json.dumps({"type": "KeepAlive"}))
                            except Exception:
                                pass
                            last_keepalive = now

                        try:
                            chunk = self._audio_q.get(timeout=0.1)
                            ws.send(chunk)
                        except queue.Empty:
                            pass
                        except Exception as e:
                            traceback.print_exc()

                threading.Thread(target=send_loop, daemon=True).start()

                #Listen for responses
                try:
                    while self._running.is_set():
                        try:
                            msg = ws.recv(timeout=0.25)
                            self.parse_response(json.loads(msg))
                            #print(msg)
                        except TimeoutError:
                            continue
                        except Exception as e:
                            traceback.print_exc()
                finally:
                    try:
                        ws.send(json.dumps({"type": "CloseStream"}))
                    except Exception:
                        pass
        threading.Thread(target=work, daemon=True).start()

def test():
    def on_transcript(result:TranscriberResult):
        print(f"{result.transcriber.__class__.__name__}")
        for t in result.transcripts:
            print(f"   {t.transcript} (confidence: {t.confidence:.03f})")
            
    transcriber = DeepgramTranscriber()
    transcriber.add_transcript_callback(on_transcript)
    transcriber.start()
    DeepgramTranscriber.PRINT_DEBUG = True
    
    if 0:
        pcm_utils.listen_on_streamed_audio([transcriber.push_pcm16_frames])
    else:
        pcm_utils.listen_on_local_mic(16000,[transcriber.push_pcm16_frames], channel_cnt=1)
    transcriber.stop()
if __name__ == "__main__":
    test()

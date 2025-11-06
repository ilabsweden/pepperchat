from dataclasses import dataclass
import json
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech
from google.api_core.client_options import ClientOptions
from google.oauth2 import service_account
import os
import queue
import sys
import threading
import time
import traceback
from typing import Callable, List
import numpy as np
from pcm_processor import PcmProcessor
import pcm_utils
import silerovad

from transcriber import Transcriber, TranscriberResult, TranscriptWord, Transcript

import dotenv
dotenv.load_dotenv()

# ---- CONFIG ----
REGION = "europe-west4"   # close to Sweden; also supported for Chirp models
LANG = "sv-SE"            # Swedish
MODEL = "chirp_2"         # try "chirp_3" if available for sv-SE in your region
_SAMPLE_RATE = 16000      # 16 kHz mono PCM (LINEAR16)

class GoogleTranscriber(Transcriber):
    PRINT_DEBUG = False
    def debug_print(self, *args, **kwargs):
        if self.PRINT_DEBUG:
            print(f"{self.__class__.__name__}:", *args, **kwargs)

    def __init__(self):
        Transcriber.__init__(self)
        self._audio_q = queue.Queue()
        self._running = threading.Event()
        self._last_pcm_recive_time = 0
        self.pcm_processor = PcmProcessor(_SAMPLE_RATE, 1, millis_per_chunk=50)
        creds = json.loads(os.getenv("GOOGLE_CLOUD_SPEECH_CREDENTIALS"))
        self._client_credentials=service_account.Credentials.from_service_account_info(creds)
        self._client_options=ClientOptions(api_endpoint=f"{REGION}-speech.googleapis.com")

        recognition_config = cloud_speech.RecognitionConfig(
            explicit_decoding_config=cloud_speech.ExplicitDecodingConfig(
                encoding=cloud_speech.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=_SAMPLE_RATE,
                audio_channel_count=1,
            ),
            language_codes=[LANG],
            model=MODEL,  
            features=cloud_speech.RecognitionFeatures(
                enable_automatic_punctuation=True,
                enable_word_confidence=True
            ),
        )

        self._config_request = cloud_speech.StreamingRecognizeRequest(
            recognizer=f"projects/{creds.get('project_id')}/locations/{REGION}/recognizers/_",
            streaming_config=cloud_speech.StreamingRecognitionConfig(config=recognition_config),
        )

    def push_pcm16_frames(self, sample_rate:int, channel_cnt:int, frames:np.ndarray):
        self._last_pcm_recive_time = time.time()
        if not self._running.is_set():
            self._start()
        for chunk in self.pcm_processor.get_frame_chunks(sample_rate, channel_cnt, frames):
            self._audio_q.put(chunk.tobytes())

    def _stop(self):
        self._audio_q.put(None)
        self._running.clear()
        self.debug_print("Stop")
        
    def _start(self):
        self._running.set()
        
        def check_time_to_die():
            timeout = .5
            while self._running.is_set():
                if time.time() - self._last_pcm_recive_time > timeout:
                    self._stop()
                time.sleep(timeout)
        threading.Thread(target=check_time_to_die, daemon=True).start()
        
        def work():
            
            # ---- GOOGLE SPEECH CLIENT ----
            
            client = SpeechClient(
                credentials=self._client_credentials,
                client_options=self._client_options,
            )
            def audio_generator():
                while True:
                    chunk = self._audio_q.get()
                    if chunk is None:
                        return
                    yield cloud_speech.StreamingRecognizeRequest(audio=chunk)
            config_request = self._config_request
            def request_iter():
                # send config once, then the audio chunks forever
                yield config_request
                yield from audio_generator()  

            while self._running.is_set():
                try:
                    responses = client.streaming_recognize(requests=request_iter())
                    for response in responses:
                        self.debug_print(response)
                        for result in response.results:
                            if result.alternatives:
                                self._on_transcribed(
                                    [Transcript(alt.transcript, alt.confidence, [TranscriptWord(w.word, w.confidence) for w in alt.words]) for alt in result.alternatives],
                                    result.is_final,
                                    result
                                )
                except:
                    traceback.print_exc()
        threading.Thread(target=work, daemon=True).start()



def test():
    GoogleTranscriber.PRINT_DEBUG = True
    silerovad.SileroVad.PRINT_DEBUG = True
    transcriber = GoogleTranscriber()
    silero = silerovad.SileroVad(
        threshold=.35,
        head_millis=1000,
        speech_stream_callback=transcriber.push_pcm16_frames,
        speech_end_callback=pcm_utils.playback_pcm16_frame_chunks
    )
    def on_transcript(result:TranscriberResult):
        alt = result.transcripts[0]
        print(f"{alt.transcript} (confidence: {alt.confidence})")

    transcriber.add_transcript_callback(on_transcript)
    if 0:
        pcm_utils.listen_on_streamed_audio([silero.push_pcm16_frames])
    else:
        pcm_utils.listen_on_local_mic(16000,[silero.push_pcm16_frames], channel_cnt=1)

if __name__ == "__main__":
    test()


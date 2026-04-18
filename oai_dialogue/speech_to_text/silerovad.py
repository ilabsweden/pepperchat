#pip install torch
#pip install silero-vad
import math
import time
from typing import List
import numpy as np
import torch
try:
    from pcm_processor import PcmProcessor
    import pcm_utils
except ImportError:
    from oai_dialogue.speech_to_text.pcm_processor import PcmProcessor
    import oai_dialogue.speech_to_text.pcm_utils as pcm_utils

class SileroVad:
    PRINT_DEBUG = False
    def debug_print(self, *args, **kwargs):
        if self.PRINT_DEBUG:
            print(f"{self.__class__.__name__}:", *args, **kwargs)

    def __init__(self, speech_stream_callback, threshold = 0.5, head_millis = 300, min_silence_duration_ms = 500, speech_end_callback = None):

        self._threshold = threshold
        self._min_silence_duration_ms = min_silence_duration_ms

        model, utils = torch.hub.load('snakers4/silero-vad', 'silero_vad', trust_repo=True)
        (_, _, _, VADIterator, _) = utils
        
        def create():
             self._vad_iterator = VADIterator(model, threshold = self._threshold, min_silence_duration_ms = self._min_silence_duration_ms)
        create()
        self._recreate = create

        self._incomlete_chunk:np.array = None 
        self._speech_detected = False
        self._last_pcm16_chunks:List[np.ndarray] = []
        self._speech_stream_callback = speech_stream_callback
        self._speech_end_callback = speech_end_callback
        self.head_millis = head_millis
        self._full_speech_pcm16_chunks:List[np.ndarray] = []
        self._pcmmgr = PcmProcessor(16000, 1, frames_per_chunk=512) # Required 16kHz, mono, chunk size 512
        print(f"{self.__class__.__name__} inited")

    @property
    def threshold(self):
        return self._threshold
    @threshold.setter
    def threshold(self, value):
        if self._threshold != value:
            self._threshold = value
            self._recreate()
    @property
    def min_silence_duration_ms(self):
        return self._min_silence_duration_ms
    @min_silence_duration_ms.setter
    def min_silence_duration_ms(self, value):
        if self._min_silence_duration_ms != value:
            self._min_silence_duration_ms = value
            self._recreate()
    

    def push_pcm16_frames(self, sample_rate:int, channel_cnt:int, frames:np.ndarray):
        pcm_dur_millis = 1000 * len(frames) / sample_rate
        if pcm_dur_millis > 0:
            self._last_pcm16_chunks.append(frames)
            max_head_chunk_cnt = math.ceil(self.head_millis / pcm_dur_millis)
            if len(self._last_pcm16_chunks) > max_head_chunk_cnt:
                self._last_pcm16_chunks.pop(0)

        for chunk in self._pcmmgr.get_frame_chunks(sample_rate, channel_cnt, frames):
            f32norm = chunk.astype(np.float32)/0xFFFF
            speech_dict = self._vad_iterator(f32norm.squeeze(), self._pcmmgr.sample_rate)
            if speech_dict:
                self._speech_detected = speech_dict.get("start")
                self.debug_print("Speech detected:", speech_dict)

        if self._speech_detected:
            while self._last_pcm16_chunks:
                pcm16_chunk = self._last_pcm16_chunks.pop(0)
                if self._speech_stream_callback:
                    self._speech_stream_callback(sample_rate, channel_cnt, pcm16_chunk)
                if self._speech_end_callback:
                    self._full_speech_pcm16_chunks.append(pcm16_chunk)
        elif self._speech_end_callback and self._full_speech_pcm16_chunks:
            self._speech_end_callback(sample_rate, channel_cnt, self._full_speech_pcm16_chunks.copy())
            self._full_speech_pcm16_chunks.clear()

def test():
    SileroVad.PRINT_DEBUG = True
    silero = SileroVad(
        threshold=.35,
        speech_stream_callback=None,
        speech_end_callback=pcm_utils.playback_pcm16_frame_chunks,
        #head_millis=1000
    )
    pcm_utils.listen_on_local_mic(16000, [silero.push_pcm16_frames], channel_cnt=1)

if __name__ == "__main__":
    test()
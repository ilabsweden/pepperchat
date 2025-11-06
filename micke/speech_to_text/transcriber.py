
from dataclasses import dataclass
import traceback
from typing import Callable, List


@dataclass
class TranscriptWord:
    word: str
    confidence: float

@dataclass
class Transcript:
    transcript: str
    confidence: float
    words: List[TranscriptWord]

@dataclass
class TranscriberResult:
    transcriber: object
    start_time: float
    duration: float
    is_final: bool
    transcripts: List[Transcript]
    additional_data: object

class Transcriber:
    def __init__(self):
        self._transcript_callbacks:List[Callable[[TranscriberResult], None]] = []

    def add_transcript_callback(self, callback:Callable[[TranscriberResult], None]):
        if callback not in self._transcript_callbacks:
            self._transcript_callbacks.append(callback)
            
    def remove_transcript_callback(self, callback:Callable[[TranscriberResult], None]):
        if callback in self._transcript_callbacks:
            self._transcript_callbacks.remove(callback)

    def _on_transcribed(self, start_time, duration, transcripts, is_final, additional_data):
        transcript_result = TranscriberResult(
            transcriber=self,
            start_time=start_time,
            duration = duration,
            is_final=is_final,
            transcripts=transcripts,
            additional_data=additional_data
        )
        for callback in self._transcript_callbacks:
            try:
                callback(transcript_result)
            except Exception as e:
                traceback.print_exc()

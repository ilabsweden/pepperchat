import re
import time
import traceback
from typing import List
from google_transcriber import GoogleTranscriber
from deepgram_transcriber import DeepgramTranscriber
from transcriber import TranscriberResult
import pcm_utils
import silerovad
import __parentdir
from comm import TranscriptSender, RobotStateListener, RobotState

class TimeSlot:
    def __init__(self):
        self.start = time.time()
        self.end = -1
    def done(self):
        self.end = time.time()
    def overlaps(self, some_start, some_dur):
        if self.end < 0:
            return some_start > self.start
        some_end = some_start + some_dur
        return self.start < some_start < self.end or self.start < some_end < self.end

def main():
    def on_transcript(result:TranscriberResult):
        robot_talking = talkslots and talkslots[-1].overlaps(result.start_time, result.duration)
        if result.is_final:
            print(f"{result.transcriber.__class__.__name__}")
            for t in result.transcripts:
                print(f"   {t.transcript} (confidence: {t.confidence:.03f})")
        if result.is_final:
            best_transcript = sorted(result.transcripts, key=lambda t: t.confidence)[-1].transcript
            if re.search(r"tack.*?det.*?räcker", best_transcript, flags=re.IGNORECASE | re.DOTALL):
                print("Gently tell the robot to stop talking")                
                transcript_sender.send("stfu")
            elif not robot_talking:
                transcript_sender.send(best_transcript)

    transcript_sender = TranscriptSender()
    talkslots:List[TimeSlot] = []

    def on_robot_state_change(state:RobotState):
        if state.talking:
            talkslots.append(TimeSlot())
        elif talkslots:
            talkslots[-1].done()
        print(state.__dict__)
    robot_state_listener = RobotStateListener(on_robot_state_change)
    if 1:
        #GoogleTranscriber.PRINT_DEBUG = True
        silerovad.SileroVad.PRINT_DEBUG = True
        transcriber = GoogleTranscriber()
        silero = silerovad.SileroVad(
            threshold=.35,
            head_millis=1000,
            speech_stream_callback=transcriber.push_pcm16_frames,
            speech_end_callback=pcm_utils.playback_pcm16_frame_chunks
        )
        audio_callback = silero.push_pcm16_frames
    else:
        transcriber = DeepgramTranscriber()
        audio_callback = transcriber.push_pcm16_frames

    transcriber.add_transcript_callback(on_transcript)
    
    if 0:
        pcm_utils.listen_on_streamed_audio([audio_callback])
    else:
        pcm_utils.listen_on_local_mic(16000,[audio_callback], channel_cnt=1)


if __name__ == "__main__":
    main()

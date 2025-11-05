import time
import traceback
from google_transcriber import GoogleTranscriber
from deepgram_transcriber import DeepgramTranscriber
from transcriber import TranscriberResult
import pcm_utils
import silerovad
from transcript_comm import TranscriptSender


def main():
    def on_transcript(result:TranscriberResult):
        if result.is_final:
            print(f"{result.transcriber.__class__.__name__}")
            for t in result.transcripts:
                print(f"   {t.transcript} (confidence: {t.confidence:.03f})")
        if result.is_final:
            best_transcript = sorted(result.transcripts, key=lambda t: t.confidence)[-1].transcript
            transcript_sender.send(best_transcript)
    transcript_sender = TranscriptSender()
    transcript_sender.send("Nisse")
    if 1:
        GoogleTranscriber.PRINT_DEBUG = True
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

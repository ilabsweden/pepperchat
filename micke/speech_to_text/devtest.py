from __future__ import print_function
import threading
import time

import numpy as np
import pyaudio
import __parentdir
import comm
from deepgram_transcriber import DeepgramTranscriber
from google_transcriber import GoogleTranscriber
from pcm_processor import PcmProcessor
import pcm_utils
import silerovad
from transcriber import TranscriberResult
import keyboard
def test_transcript_receiver():
    def onrec(msg):
        print(msg)
    receiver = comm.TranscriptReceiver(onrec)
    while True:
        time.sleep(.1)

def test_state_reporter():
    reporter = comm.RobotStateReporter()
    talking = False
    while True:
        talking = not talking
        reporter.report_talking(talking)
        time.sleep(.5)

def test_state_listener():
    def on_change(state):
        print(state.__dict__)
    listener = comm.RobotStateListener(on_change)
    while True:
        time.sleep(.1)

def test_state_comm():
    t = threading.Thread(target=test_state_reporter)
    t.setDaemon(True)
    t.start()
    test_state_listener()

import wave
def xx():
    SAMPLE_RATE = 16000
    BLOCK_SIZE = 1024
    w = wave.open("pladder.wav", "rb",)
    p = pyaudio.PyAudio()
    outstream = p.open(
        rate=SAMPLE_RATE,
        channels=1,
        output=True,
        format=pyaudio.paInt16,
        
    )
    def mix_int16(a: np.ndarray, b: np.ndarray, gain_a=1.0, gain_b=1.0, headroom_db=6.0):
        """
        Mix two identical-shape int16 audio frames (mono or multi-channel).
        Optional per-input gains and global headroom.
        """
        assert a.dtype == np.int16 and b.dtype == np.int16
        # Optional: handle mismatched lengths by trimming to min
        n = min(len(a), len(b))
        a = a[:n]
        b = b[:n]

        # Convert to float for clean gain, add headroom
        hr = 10 ** (-headroom_db / 20.0)  # e.g., 6 dB -> ~0.501
        af = a.astype(np.float32) * (gain_a * hr)
        bf = b.astype(np.float32) * (gain_b * hr)

        mixed = af + bf
        mixed = np.clip(mixed, -32768.0, 32767.0)
        return mixed.astype(np.int16)    
    pladdra = threading.Event()
    def keycheck():
        def listen():
            while True: 
                try:
                    if keyboard.is_pressed('q'):  # if key 'q' is pressed 
                        pladdra.set()
                    else:
                        pladdra.clear()
                except:
                    pass
                time.sleep(.01)
        threading.Thread(target=listen, daemon=True).start()
    keycheck()
    def on_transcript(result:TranscriberResult):
        for alt in result.transcripts:
            print("FINAL:" if result.is_final else " "*6, f"{alt.transcript} (confidence: {alt.confidence}, start_time:{result.start_time}, duration:{result.duration})")

        #print(result)
    if 0:
        transcriber = DeepgramTranscriber()
        frame_receiver = transcriber.push_pcm16_frames
    else:
        #GoogleTranscriber.PRINT_DEBUG=True
        transcriber = GoogleTranscriber()
        silero = silerovad.SileroVad(
            threshold=.35,
            head_millis=1000,
            speech_stream_callback=transcriber.push_pcm16_frames,
            #speech_end_callback=pcm_utils.playback_pcm16_frame_chunks
        )
        silero.PRINT_DEBUG = True
        frame_receiver = silero.push_pcm16_frames

    transcriber.add_transcript_callback(on_transcript)

    def on_mic(sample_rate:int, channel_cnt:int, mic_frames:np.ndarray):
        file_frames = np.frombuffer(w.readframes(BLOCK_SIZE), dtype=np.int16)
        if len(file_frames) < BLOCK_SIZE:
            w.rewind()
            file_frames = np.frombuffer(w.readframes(BLOCK_SIZE), dtype=np.int16)
        if pladdra.is_set():
            file_frames = file_frames // 16
        else:
            file_frames = file_frames * 0
        mixed_frames = mix_int16(file_frames, mic_frames)
        outstream.write(file_frames.tobytes())
        frame_receiver(sample_rate, channel_cnt, mixed_frames)
    pcm_utils.listen_on_local_mic(SAMPLE_RATE, [on_mic], blocksize=BLOCK_SIZE)
    outstream.close()
    p.terminate()

    # while bajts := w.readframes(1024):
    #     print(bajts)
    # pass
def aec():
    pass
def test_google():
    ts = comm.TranscriptSender()
    #GoogleTranscriber.PRINT_DEBUG = True
    silerovad.SileroVad.PRINT_DEBUG = True
    transcriber = GoogleTranscriber()
    silero = silerovad.SileroVad(
        threshold=.35,
        head_millis=1000,
        speech_stream_callback=transcriber.push_pcm16_frames,
        speech_end_callback=pcm_utils.playback_pcm16_frame_chunks
    )
    def on_transcript(result:TranscriberResult):
        if result.is_final:
            alt = result.transcripts[0]
            print(f"{alt.transcript} (confidence: {alt.confidence}, start_time:{result.start_time}, duration:{result.duration})")
            ts.send(alt.transcript)
        #print(result)

    transcriber.add_transcript_callback(on_transcript)
    if 0:
        pcm_utils.listen_on_streamed_audio([silero.push_pcm16_frames])
    else:
        pcm_utils.listen_on_local_mic(16000,[silero.push_pcm16_frames], channel_cnt=1)

test_google()
#aec()
#xx()
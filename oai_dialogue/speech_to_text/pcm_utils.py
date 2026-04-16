import queue
import threading
import time
import traceback
from typing import Callable, Iterable, List, Optional
import numpy as np
import pyaudio
try:
    import audio_stream
    from pcm_processor import PcmProcessor
except ImportError:
    import oai_dialogue.audio_stream as audio_stream
    from oai_dialogue.speech_to_text.pcm_processor import PcmProcessor

def playback_pcm16_frame_chunks(sample_rate:int, channel_cnt:int, pcm16_chunks:List[np.ndarray], wait = False):
    def playit():
        p = pyaudio.PyAudio()
        outstream = p.open(
            rate= sample_rate,
            channels=channel_cnt,
            output=True,
            format=pyaudio.paInt16,
            
        )
        for chunk in pcm16_chunks:
            outstream.write(chunk.tobytes())
        outstream.close()
        p.terminate()
    if wait:
        playit()
    else:
        threading.Thread(target=playit, daemon=True).start()

def listen_on_local_mic(sample_rate, callbacks:List[Callable[[int, int, np.ndarray], None]], blocksize = 1024, channel_cnt = 1):
    p = pyaudio.PyAudio()
    instream = None
    try:
        dev_idx = None
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info["maxInputChannels"] >= channel_cnt:
                print(info)
                dev_idx = i
                break

        instream = p.open(
            input_device_index=dev_idx,
            rate=sample_rate,
            channels=channel_cnt,
            input=True,
            format=pyaudio.paInt16,
            frames_per_buffer=blocksize
        )

        while True:
            try:
                data = instream.read(blocksize, exception_on_overflow=False)
                frames = np.frombuffer(data, dtype=np.int16).copy()
                for callback in callbacks:
                    callback(sample_rate, channel_cnt, frames)
            except KeyboardInterrupt:
                return
            except OSError as exc:
                err_no = getattr(exc, "errno", None)
                message = str(exc).lower()
                if err_no == -9988 or "stream closed" in message:
                    print(f"Microphone stream closed ({exc}). Stopping local mic listener.")
                    return
                print(f"Microphone stream error: {exc}")
                return
            except Exception:
                try:
                    print(traceback.format_exc())
                except Exception:
                    print("Unexpected microphone error (failed to format traceback).")
                return
    finally:
        try:
            if instream is not None:
                instream.stop_stream()
                instream.close()
        except Exception:
            pass
        p.terminate()


def listen_on_streamed_audio(callbacks:List[Callable[[int, int, np.ndarray], None]]):
    with audio_stream.AudioStreamReceiver(audio_stream.DEFAULT_UDP_PORT, audio_stream.DEFAULT_MULTICAST_IP) as audio_receiver:
        for callback in callbacks:
            audio_receiver.add_pcm_callback(callback)
        try:
            while True:
                time.sleep(.1)
        except:
            pass


class AsyncAudioPlayer:
    def __init__(self, sample_rate, channel_cnt = 1):
        self._running = threading.Event()
        self._queue = queue.Queue()
        self._pcm_processor = PcmProcessor(sample_rate, 1, millis_per_chunk=100)
        def loop():
            self._running.set()
            p = pyaudio.PyAudio()
            outstream = p.open(
                rate= sample_rate,
                channels=channel_cnt,
                output=True,
                format=pyaudio.paInt16,
                
            )
            while self._running.is_set():
                outstream.write(self._queue.get().tobytes())
            outstream.close()
            p.terminate()

            # with sd.RawOutputStream(samplerate=sample_rate, channels=channels, dtype="int16") as out:
            #     while self._running.is_set():
            #         out.write(self._queue.get().tobytes())
        threading.Thread(target=loop, daemon=True).start()                

    def is_playing(self):
        return not self._queue.empty()
    
    def clear_queue(self):
        try:
            while True:
                self._queue.get_nowait()
        except:
            pass    

    def push_pcm16_frames(self, sample_rate:int, channel_cnt:int, frames:np.ndarray):
        for chunk in self._pcm_processor.get_frame_chunks(sample_rate, channel_cnt, frames):
            self._queue.put(chunk)

def test():
    mgr = PcmProcessor(16000,1)#,millis_per_chunk=50)#,samples_per_chunk=320)

    coll_chunks = []
    last_pb = 0
    def mic_callback(sample_rate, channel_cnt, frames):
        nonlocal coll_chunks, last_pb
        coll_chunks += mgr.get_frame_chunks(sample_rate, channel_cnt, frames)
        #print(len(frames),len(coll_chunks),mgr.frames_per_chunk)
        if coll_chunks and time.time() - last_pb > 1:
            last_pb = time.time()
            print("pb")
            playback_pcm16_frame_chunks(mgr.sample_rate, mgr.channel_cnt, coll_chunks.copy())
            coll_chunks = []
    listen_on_local_mic(16000, [mic_callback], channel_cnt=1)
if __name__ == "__main__":
    test()
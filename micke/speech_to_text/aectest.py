import time
import numpy as np, sounddevice as sd
from scipy.io import wavfile
from scipy.signal import resample_poly
import aec_audio_processing as a

SR = 16000

def load_robot_frames(path, sr=SR):
    fs, x = wavfile.read(path)
    if x.ndim == 2:
        x = x.mean(axis=1)
    if fs != sr:
        x = resample_poly(x.astype(np.float32), sr, fs)
    x = np.clip(x, -32768, 32767).astype(np.int16)
    pos = 0
    while True:
        yield x[pos:pos+frame] if pos+frame <= len(x) else np.concatenate(
            [x[pos:], np.zeros(frame-(len(x)-pos), np.int16)]
        )
        pos = (pos + frame) % len(x)

# --- init APM ---
apm = a.AudioProcessor(enable_aec=True, enable_ns=True, ns_level=2,
                       enable_agc=False, enable_vad=False)
apm.set_stream_format(SR, 1)
apm.set_reverse_stream_format(SR, 1)
frame = apm.get_frame_size()               # should be 160 at 16k
# Optional delay hint:
#apm.set_stream_delay(10)

robot_gen = load_robot_frames("pladder.wav", SR)

# for dev in sd.query_devices():
#     print(dev)
# print(sd.query_devices())
# exit()
cleanstream = sd.OutputStream(channels=1, 
               samplerate=SR, 
               dtype='int16',
               blocksize=frame, 
               device=6,
               
            )
cleanstream.start()
def callback(indata, outdata, frames, time, status):
    if status:
        print("Audio status:", status)
    assert frames == frame, f"Device delivered {frames}, AEC expects {frame}"

    far  = next(robot_gen)                 # int16[frame]
    outdata[:] = far.reshape(-1,1)         # play robot to speakers
    near = indata[:,0].copy().astype(np.int16)

    # reverse then capture
    apm.process_reverse_stream(far.tobytes())
    out_bytes = apm.process_stream(near.tobytes())
    cleaned = np.frombuffer(out_bytes, dtype=np.int16)
    cleanstream.write(cleaned)
    #cleanstream.write(indata)

    # TODO: send `cleaned` to your ASR or a file/stream
    # (Don't route cleaned back to outdata here, or you'll create a loop.)

with sd.Stream(channels=1, 
               samplerate=SR, 
               dtype='int16',
               blocksize=frame, 
               latency='low', 
               callback=callback,
            ):
    print("Running… Ctrl+C to stop.")
    while True:
        time.sleep(.1)
    #sd.sleep(60_000)

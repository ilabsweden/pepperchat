import numpy as np
import scipy.io.wavfile as wav
import matplotlib.pyplot as plt
from lms import lms_filter            # neu: kein _safe-Alias mehr

# ------------------------------------------------------------
# helpers
# ------------------------------------------------------------
def normalize_to_int16(sig: np.ndarray) -> np.ndarray:
    """Scale float signal to the full int16 range (±32767)."""
    sig = np.nan_to_num(sig)                      # replace NaNs
    peak = np.max(np.abs(sig))
    if peak > 0:
        sig = sig / peak
    return np.int16(np.clip(sig * 32767, -32768, 32767))


def process_wav_file(inp: str, out: str):
    """Run LMS AEC on a single WAV file and write the result."""
    fs, y = wav.read(inp)                # y is int16
    x = y.astype(np.float32) / 32768.0   # scale to ±1

    # stereo → mono
    if x.ndim == 2:
        x = x.mean(axis=1)

    # LMS parameters
    f0 = np.zeros(1024, dtype=np.float32)
    mus = [1e-4, 5e-4, 1e-3]             # realistic μ list

    e, *_ = lms_filter(
        desired_signal=x,
        reference_input=x,               # self-echo demo
        filter_coeff=f0,
        step_sizes=mus,
        safe=True                        # clips err to ±1e4
    )

    wav.write(out, fs, normalize_to_int16(e))
    return x, e, fs


def plot_signals(orig, filt):
    plt.figure(figsize=(12, 5))
    plt.plot(orig,  label="Original")
    plt.plot(filt,  label="AEC output", alpha=0.7)
    plt.title("Original vs. Filtered (AEC)")
    plt.legend(); plt.tight_layout(); plt.show()

# ------------------------------------------------------------
# main
# ------------------------------------------------------------
if __name__ == "__main__":
    in_wav  = "input_audio.wav"
    out_wav = "filtered_audio.wav"

    orig, filt, sr = process_wav_file(in_wav, out_wav)
    plot_signals(orig, filt)
    print(f"✓ Filtered audio written to {out_wav}")

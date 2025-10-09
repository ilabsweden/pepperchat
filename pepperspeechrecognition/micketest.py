import time, sys
import mickestubs

def test_srm():
    from speechrecognition_deepgram import SpeechRecognitionModule
    srm = SpeechRecognitionModule("Nisse", "localhost")
    srm.start()
    srm.enableAutoDetection()
    srm.calibrate()
    while True:
        time.sleep(.1)


def test_py2sender():
    from mic_stream import MicStreamConfig, MicStreamSender
    cfg = MicStreamConfig()
    sender = MicStreamSender(cfg)
    frames_per_buffer = cfg.get_frames_per_packet()
    stream, dev_name = mickestubs.get_pyaudio_input_stream(cfg.sample_rate, cfg.channel_cnt, frames_per_buffer)
    try:
        while True:
            pcm = stream.read(frames_per_buffer, exception_on_overflow=False)
            sender.send_pcm(pcm)
            print(dev_name, cfg.get_peak_bar(pcm))

    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        sender.close()

def test_py3receiver():
    from mic_stream import MicStreamConfig, MicStreamReceiver
    import sounddevice as sd
    cfg = MicStreamConfig()
    out = sd.RawOutputStream(samplerate=cfg.sample_rate, channels=cfg.channel_cnt, dtype=cfg.sample_fmt)
    out.start()
    def pcm_callback(pcm):
        out.write(pcm)
        print(cfg.get_peak_bar(pcm))
    receiver = MicStreamReceiver(cfg, pcm_callback)
    receiver.listen()
    try:
        while True:
            time.sleep(.1)
    except KeyboardInterrupt:
        pass
    finally:
        receiver.close()
        out.close()

if __name__ == "__main__":
    if "send" in sys.argv:
        test_py2sender()
    elif "rec" in sys.argv:
        test_py3receiver()
    elif "srm" in sys.argv:
        test_srm()

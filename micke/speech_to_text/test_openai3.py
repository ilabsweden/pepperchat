import dotenv
dotenv.load_dotenv()
import os, json, base64, threading, queue, time
import numpy as np
import sounddevice as sd
from websocket import WebSocketApp

# ----- Config -----
API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-realtime"          # or: gpt-4o-realtime-preview, gpt-realtime-mini
SAMPLE_RATE = 24000             # Realtime API expects PCM16 mono ~24 kHz
CHUNK_MS = 30                   # ~30 ms frames
VOICE = "alloy"                 # alloy, verse, coral, etc.
SERVER_VAD = True               # let the server detect turn-taking
INSTRUCTIONS = "Du är den svensktalande roboten Pepper."
# -------------------

assert API_KEY, "Set OPENAI_API_KEY in your environment."

WS_URL = f"wss://api.openai.com/v1/realtime?model={MODEL}"

# Audio out: write raw PCM16 to an output stream
play_queue: "queue.Queue[bytes]" = queue.Queue()

def audio_player():
    with sd.RawOutputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as out:
        while True:
            chunk = play_queue.get()
            if chunk is None:
                break
            out.write(chunk)

def float_to_pcm16(float32):
    float32 = np.clip(float32, -1.0, 1.0)
    return (float32 * 32767.0).astype(np.int16).tobytes()

def on_open(ws):
    print("✅ WebSocket connected. Sending session.update...")
    # Configure session: voice, formats, VAD, and instructions
    session_update = {
        "type": "session.update",
        "session": {
            "voice": VOICE,
            "instructions": INSTRUCTIONS,
            "turn_detection": {"type": "server_vad"} if SERVER_VAD else {"type": "none"},
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_transcription": {
                "model": "gpt-4o-mini-transcribe",   # or gpt-4o-transcribe / whisper-1
                "language": "sv"
            } ,
            #"temperature": 0.7,
            #"max_output_tokens": 50,
            #"modalities": ["text"],                      
            "modalities": ["audio", "text"],                      
        },
    }
    ws.send(json.dumps(session_update))

    # Start microphone capture on a background thread
    threading.Thread(target=stream_microphone, args=(ws,), daemon=True).start()
    # Start speaker playback thread
    threading.Thread(target=audio_player, daemon=True).start()

def stream_microphone(ws):
    """Continuously capture mic audio and append to input buffer in small chunks.
       With server VAD, you don't need to send commit/response.create."""
    blocksize = int(SAMPLE_RATE * (CHUNK_MS / 1000.0))  # samples per chunk
    print("🎙️ Mic streaming... (Ctrl+C to quit)")
    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
            while True:
                data, _ = stream.read(blocksize)  # bytes
                # Encode base64 and send append event
                evt = {
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(bytes(data)).decode("ascii"),
                }
                ws.send(json.dumps(evt))
                # (When SERVER_VAD is enabled, the server commits automatically)
                # throttle a bit to avoid tight loop
                time.sleep(CHUNK_MS / 1000.0)
    except Exception as e:
        print("Mic error:", e)
        try:
            ws.close()
        except:
            pass

def on_message(ws, message):
    # The server sends JSON text messages with events.
    # We care about response.audio.delta for audio chunks and response.completed to mark end.
    try:
        evt = json.loads(message)
    except Exception:
        # Some servers may send non-JSON frames (unlikely). Ignore.
        return

    t = evt.get("type", "")
    if t == "response.audio.delta":
        # Base64 PCM16 chunk from the assistant
        b = base64.b64decode(evt.get("delta", ""))
        play_queue.put(b)
    elif ".delta" in t:
        pass
        #print (t,evt.get("delta"))
    elif t == "error":
        print("❌ Realtime error:", evt)
    elif t == "conversation.item.input_audio_transcription.completed":
        print("USER:", evt.get("transcript"))
    elif t == "response.audio_transcript.done":
        print("ROBOT:", evt.get("transcript"))
    # Debug other events:
    # else:
    #     print("evt:", t)

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws, code, msg):
    print("🔌 WebSocket closed:", code, msg)
    play_queue.put(None)

def main():
    headers = [
        "Authorization: Bearer " + API_KEY,
        "OpenAI-Beta: realtime=v1",
    ]
    ws = WebSocketApp(
        WS_URL,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.run_forever()  # blocking

if __name__ == "__main__":
    main()

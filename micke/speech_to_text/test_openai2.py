# pip install aiohttp sounddevice numpy websocket-client
import asyncio, websockets, json, base64, numpy as np, sounddevice as sd, os
import signal
import dotenv
dotenv.load_dotenv()
API_KEY = os.environ["TMP_OPENAI_API_KEY"]


MODEL   = "gpt-4o-realtime-preview"  # eller det senaste realtime-modellnamnet
URL     = f"wss://api.openai.com/v1/realtime?model={MODEL}"

SAMPLE_RATE = 16000  # 16 kHz mono PCM16

async def stream_mic():
    async with websockets.connect(
        URL,
        extra_headers={
            "Authorization": f"Bearer {API_KEY}",
            "OpenAI-Beta": "realtime=v1"
        }
    ) as ws:
        # Konfigurera sessionen för svensk transkribering
        await ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "input_audio_format": { "type": "pcm16", "sample_rate_hz": SAMPLE_RATE },
                "transcription": { "language": "sv" },   # <- svenska
                "modalities": ["text"]                   # vi vill få text ut
            }
        }))

        # Starta en respons (så modellen börjar transkribera inkommande ljud)
        #await ws.send(json.dumps({ "type": "response.create" }))

        send_queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        # Mic callback pushes PCM chunks into an asyncio queue
        def mic_callback(indata, frames, time, status):
            if status:
                print(status, flush=True)
            pcm_bytes = (indata[:, 0] * 32767).astype(np.int16).tobytes()
            b64 = base64.b64encode(pcm_bytes).decode("utf-8")
            loop.call_soon_threadsafe(send_queue.put_nowait, b64)

        # Task: take audio from queue -> send to server
        async def sender():
            while True:
                b64 = await send_queue.get()
                await ws.send_json({
                    "type": "input_audio_buffer.append",
                    "audio": b64
                })

        async def receiver():
            async for msg in ws:
                evt = json.loads(msg.data)
                t = evt.get("type")
                if "response.audio." in t:
                    if data := evt.get("delta"):
                        evt["delta"] = f"ljuddata ({len(data)})"
                print("EVT:",evt)

                # Partials of your input (if provided)
                if t == "conversation.item.input_audio_transcription.delta":
                    chunk = evt.get("delta", "")
                    if chunk:
                        print(chunk, end="", flush=True)

                # Final transcript of your input
                elif t == "conversation.item.input_audio_transcription.completed":
                    final_txt = evt.get("transcript", "")
                    if final_txt:
                        print(final_txt, flush=True)

                # Ignore any audio the model might try to produce
                elif t.startswith("response.audio."):
                    continue

                # Log server errors
                elif t == "error":
                    print("\n[Realtime error]", evt, flush=True)
        
        print("Speak Swedish – streaming transcription is running. Press Ctrl+C to stop.")

        # Start audio stream & tasks
        stream = sd.InputStream(
            channels=1, samplerate=SAMPLE_RATE, dtype="float32", callback=mic_callback
        )
        with stream:
            sender_task = asyncio.create_task(sender())
            receiver_task = asyncio.create_task(receiver())

            # Handle Ctrl+C cleanly
            stop = asyncio.Event()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, stop.set)
                except NotImplementedError:
                    # Windows may not allow add_signal_handler for SIGTERM; Ctrl+C still works.
                    pass
            print("asdf")
            await stop.wait()
            print("dfj")
            sender_task.cancel()
            receiver_task.cancel()
            try:
                await sender_task
            except asyncio.CancelledError:
                pass
            try:
                await receiver_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    asyncio.run(stream_mic())


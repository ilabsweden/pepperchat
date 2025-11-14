# pip install aiohttp sounddevice numpy
import asyncio, aiohttp, json, base64, numpy as np, sounddevice as sd, os, signal
import dotenv
dotenv.load_dotenv()
API_KEY = os.environ["TMP_OPENAI_API_KEY"]
MODEL   = "gpt-4o-realtime-preview"   # update to the latest realtime model if needed
MODEL   = "gpt-realtime"   # update to the latest realtime model if needed

URL     = f"wss://api.openai.com/v1/realtime?model={MODEL}"

SAMPLE_RATE = 16000  # 16 kHz mono PCM16

async def stream_mic():
    # aiohttp needs headers as a dict
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }

    async with aiohttp.ClientSession() as session:
        
        async with session.ws_connect(URL, headers=headers) as ws:
            print(ws)
        
            # Configure the session for Swedish transcription
            # await ws.send_json({
            #     "type": "session.update",
            #     "session": {
            #         "input_audio_format": {"type": "pcm16", "sample_rate_hz": SAMPLE_RATE},
            #         "turn_detection": {"type": "server_vad"},
            #         "transcription": {"language": "sv"},
            #         "modalities": ["text"],
            #     }
            # })
            # await ws.send_json({
            #     "type": "session.update",
            #     "session": {
            #         "object": "realtime.session",
            #         "type": "transcription",
            #         "id": "session_abc123",
            #         "audio": {
            #             "input": {
            #                 "format": {
            #                     "type": "audio/pcm",
            #                     "rate": SAMPLE_RATE
            #                 },
            #                 "noise_reduction": {
            #                     "type": "near_field"
            #                 },
            #                 "transcription": {
            #                     "model": "gpt-4o-transcribe",
            #                     "prompt": "",
            #                     "language": "en"
            #                 },
            #                 "turn_detection": {
            #                     "type": "server_vad",
            #                     "threshold": 0.5,
            #                     "prefix_padding_ms": 300,
            #                     "silence_duration_ms": 500
            #                 }
            #             }
            #         },
            #         "include": [
            #             "item.input_audio_transcription.logprobs"
            #         ]
            #     }
            # })
            await ws.send_json({
                "type": "session.update",
                "session": {
                    "input_audio_format": "pcm16",
                    #"transcription": {"language": "sv"},
                    "modalities": ["text"],
                    #"type": "transcription",
                    # "id": "session_abc123",
                    # "audio": {
                    #     "input": {
                    #         "format": {
                    #             "type": "audio/pcm",
                    #             "rate": SAMPLE_RATE
                    #         },
                    #         "noise_reduction": {
                    #             "type": "near_field"
                    #         },
                    #         "transcription": {
                    #             "model": "gpt-4o-transcribe",
                    #             "prompt": "",
                    #             "language": "en"
                    #         },
                    #         "turn_detection": {
                    #             "type": "server_vad",
                    #             "threshold": 0.5,
                    #             "prefix_padding_ms": 300,
                    #             "silence_duration_ms": 500
                    #         }
                    #     }
                    # },
                    # "include": [
                    #     "item.input_audio_transcription.logprobs"
                    # ]
                }
            })            
            # # Start a response so the model begins emitting deltas
            # await ws.send_json({ 
            #     "type": "response.create" 
            # })

            loop = asyncio.get_running_loop()
            send_queue = asyncio.Queue()

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

            event_types = []
            # Task: read server events -> print partial/final transcripts
            async def _receiver():
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue
                    evt = json.loads(msg.data)
                    t = evt.get("type")

                    # --- print partial text as it streams ---
                    if t in ("response.audio_transcript.delta", "response.output_text.delta", "response.delta"):
                        # Most transcript deltas come here:
                        chunk = evt.get("delta") or ""
                        if chunk:
                            print(chunk, end="", flush=True)

                    # --- print finalized text and start a new turn ---
                    elif t in ("response.audio_transcript.done", "response.output_text.done", "response.completed", "response.done"):
                        final_txt = evt.get("transcript") or evt.get("output_text") or ""
                        if final_txt:
                            print(final_txt, end="", flush=True)
                        print()  # newline after a finalized segment

                        # Ask the server to begin a fresh response for the next VAD turn
                        await ws.send_json({ "type": "response.create" })

                    # (Optional) Log errors for visibility
                    elif t == "error":
                        print("\n[Realtime error]", evt, flush=True)
            async def receiver():
                async for msg in ws:
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue
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

                await stop.wait()
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

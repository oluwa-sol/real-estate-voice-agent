import asyncio
import json
import os

from dotenv import load_dotenv
load_dotenv()  # Must run before any other import reads os.getenv()

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agent import build_greeting, build_system_prompt, get_claude_response, text_to_speech
from airtable_client import get_leads, get_next_showing

# v3 streaming endpoint — auth goes in Authorization header, not URL
AAI_WS_URL = "wss://streaming.assemblyai.com/v3/ws?speech_model=universal-3-5-pro&sample_rate=16000"

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/leads")
async def leads_list():
    """Frontend fetches this on page load to show the selectable lead list."""
    leads = await get_leads()
    if not leads:
        return []
    return leads


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Client sends the selected lead as first message
    try:
        first = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        lead = first.get("lead")
    except Exception:
        lead = None

    if not lead:
        await websocket.send_json({"type": "error", "message": "No lead selected."})
        await websocket.close()
        return

    system_prompt = build_system_prompt(lead)
    conversation_history = []

    # Send greeting
    greeting_text = build_greeting(lead)
    await websocket.send_json({"type": "agent_speaking", "text": greeting_text})
    tts_ok = False
    try:
        greeting_audio = await text_to_speech(greeting_text)
        await websocket.send_bytes(greeting_audio)
        tts_ok = True
    except Exception as e:
        print(f"TTS skipped (browser will speak): {e}")
    await websocket.send_json({"type": "agent_done", "tts_failed": not tts_ok})
    conversation_history.append({"role": "assistant", "content": greeting_text})

    # Connect to AssemblyAI Realtime STT (v3)
    try:
        aai_ws = await websockets.connect(
            AAI_WS_URL,
            additional_headers={"Authorization": os.getenv("ASSEMBLYAI_KEY")},
        )
    except Exception as e:
        await websocket.send_json({"type": "error", "message": f"AssemblyAI connection failed: {str(e)}"})
        await websocket.close()
        return

    # Wait for AssemblyAI Begin message
    session_msg = await aai_ws.recv()
    session_data = json.loads(session_msg)
    if session_data.get("type") != "Begin":
        await websocket.send_json({"type": "error", "message": f"AssemblyAI unexpected open message: {session_data}"})
        await websocket.close()
        return

    is_agent_speaking = False

    async def receive_audio_from_browser():
        """Forward mic audio from browser to AssemblyAI."""
        nonlocal is_agent_speaking
        try:
            while True:
                data = await websocket.receive()
                if data["type"] == "websocket.disconnect":
                    break
                if data.get("bytes") and not is_agent_speaking:
                    await aai_ws.send(data["bytes"])
                elif data.get("text"):
                    msg = json.loads(data["text"])
                    if msg.get("type") == "stop":
                        break
        except WebSocketDisconnect:
            pass

    async def process_transcripts():
        """Receive transcripts from AssemblyAI, call Claude, send TTS back."""
        nonlocal is_agent_speaking
        try:
            async for raw_msg in aai_ws:
                msg = json.loads(raw_msg)

                if msg.get("type") == "Turn" and not msg.get("end_of_turn"):
                    text = msg.get("transcript", "").strip()
                    if text:
                        await websocket.send_json({"type": "partial", "text": text})

                elif msg.get("type") == "Turn" and msg.get("end_of_turn"):
                    text = msg.get("transcript", "").strip()
                    if not text:
                        continue

                    await websocket.send_json({"type": "transcript", "text": text})
                    conversation_history.append({"role": "user", "content": text})

                    is_agent_speaking = True
                    await websocket.send_json({"type": "processing"})

                    try:
                        response_text = await get_claude_response(conversation_history, system_prompt)
                        conversation_history.append({"role": "assistant", "content": response_text})

                        await websocket.send_json({"type": "agent_speaking", "text": response_text})
                        tts_ok = False
                        try:
                            audio_bytes = await text_to_speech(response_text)
                            await websocket.send_bytes(audio_bytes)
                            tts_ok = True
                        except Exception as tts_err:
                            print(f"TTS skipped (browser will speak): {tts_err}")
                        await websocket.send_json({"type": "agent_done", "tts_failed": not tts_ok})

                    except Exception as e:
                        await websocket.send_json({"type": "error", "message": str(e)})
                    finally:
                        is_agent_speaking = False

        except websockets.exceptions.ConnectionClosed:
            pass

    try:
        await asyncio.gather(
            receive_audio_from_browser(),
            process_transcripts(),
        )
    finally:
        await aai_ws.close()

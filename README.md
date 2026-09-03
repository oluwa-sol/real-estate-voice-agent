# Real Estate Voice Agent

A real-time voice briefing assistant for real estate agents. Built for the AssemblyAI Voice Agent Hackathon.

## What It Does

Real estate agents juggle multiple leads across WhatsApp, Instagram, and web forms. Before a showing, they need to quickly recall who they're meeting, what the lead wants, their budget, and how to approach them.

This voice agent solves that. The agent opens the app, selects an upcoming lead, clicks Start Briefing, and has a natural voice conversation to get up to speed in under two minutes. Hands-free, right before walking through the door.

**Live demo:** https://web-production-99b82.up.railway.app

## How It Works

```
Lead comes in (WhatsApp / Instagram / Typeform)
        ↓
n8n workflows qualify, score, and book the viewing
        ↓
Lead data stored in Airtable CRM
        ↓
Agent opens voice briefing app before the showing
        ↓
AssemblyAI transcribes agent's voice in real time
        ↓
Claude answers questions from the lead's Airtable profile
        ↓
ElevenLabs speaks the response back
```

The voice agent is the final layer on top of an existing 5-workflow real estate CRM, not a standalone prototype.

## Tech Stack

| Layer | Tool |
|---|---|
| Real-time STT | AssemblyAI Streaming v3 |
| AI responses | Claude Haiku (Anthropic) |
| Text-to-speech | ElevenLabs |
| CRM / lead data | Airtable |
| Backend | FastAPI + WebSockets |
| Frontend | Vanilla JS (Web Audio API) |
| Deployment | Railway |

## Running Locally

**1. Clone the repo**
```bash
git clone https://github.com/oluwa-sol/real-estate-voice-agent.git
cd real-estate-voice-agent
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Set up environment variables**
```bash
cp .env.example .env
# Fill in your API keys
```

Required keys in `.env`:
```
ASSEMBLYAI_KEY=
CLAUDE_API_KEY=
ELEVENLABS_KEY=
ELEVENLABS_VOICE_ID=
AIRTABLE_TOKEN=
AIRTABLE_BASE_ID=
```

**4. Run the server**
```bash
python -m uvicorn main:app --reload
```

Open http://localhost:8000

## Project Structure

```
main.py           # FastAPI app + WebSocket handler
agent.py          # Claude + ElevenLabs logic
airtable_client.py # Airtable lead fetching
static/index.html # Browser UI
requirements.txt
Procfile          # Railway deployment
```

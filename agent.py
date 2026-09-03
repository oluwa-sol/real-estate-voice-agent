import os
import httpx
import anthropic

ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

def _claude():
    return anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))


def build_system_prompt(lead: dict) -> str:
    transcript_section = (
        f"\nVoice note from lead:\n{lead['voice_transcript']}"
        if lead.get("voice_transcript")
        else ""
    )

    return f"""You are a real estate briefing assistant helping an agent prepare for a showing.
You know everything about this lead and answer questions concisely in natural spoken English.
Keep every response under 40 words — this is a voice call, not a document.
Never use bullet points, headers, or lists. Speak in short, natural sentences.
End responses with a brief pause cue like "anything else?" or stay silent if the agent seems done.

LEAD PROFILE:
Name: {lead['name']}
Property interest: {lead['property_interest']}
Budget: {lead['budget']}
Intent: {lead['intent']}
Urgency: {lead['urgency']}
Lead temperature: {lead['tag']} (score: {lead['score']})
Platform they came from: {lead['platform']}
Original message: {lead['message']}{transcript_section}
Viewing date: {lead['viewing_date']}

Start by greeting the agent and giving a one-sentence summary of who they're about to see.
Then wait for the agent to ask questions or say "start briefing" for the full rundown."""


def build_greeting(lead: dict) -> str:
    name = lead["name"] or "your lead"
    budget = lead["budget"] or "unspecified budget"
    prop = lead["property_interest"] or "a property"
    tag = lead["tag"] or ""

    tag_note = ""
    if tag == "HOT":
        tag_note = " They're a hot lead, high intent."
    elif tag == "COLD":
        tag_note = " They're cold, tread carefully."

    return (
        f"Hey, you have a showing coming up with {name}. "
        f"They're looking for {prop}, budget around {budget}.{tag_note} "
        f"Ask me anything about them, or say 'full briefing' and I'll walk you through everything."
    )


async def get_claude_response(history: list, system_prompt: str) -> str:
    response = _claude().messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=120,
        system=system_prompt,
        messages=history,
    )
    return response.content[0].text.strip().replace("—", ",").replace("–", ",")


async def text_to_speech(text: str) -> bytes:
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "xi-api-key": os.getenv("ELEVENLABS_KEY"),
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, headers=headers, json=body)
        if not resp.is_success:
            print(f"ElevenLabs {resp.status_code}: {resp.text}")
        resp.raise_for_status()
        return resp.content

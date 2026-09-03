import os
import httpx
from datetime import date

AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID", "appJfSt8YbO1NAWjA")
BASE_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"

HEADERS = lambda: {"Authorization": f"Bearer {os.getenv('AIRTABLE_TOKEN')}"}


async def get_leads(max_records: int = 6) -> list:
    """Return all leads sorted by score descending, for the selection list."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{BASE_URL}/Leads",
            headers=HEADERS(),
            params={
                "sort[0][field]": "Score",
                "sort[0][direction]": "desc",
                "maxRecords": max_records,
            },
        )
        data = resp.json()
        return [_clean(r["fields"], r["id"]) for r in data.get("records", [])]


async def get_next_showing() -> dict | None:
    """
    Returns the next upcoming lead with Status = 'Viewing Booked'.
    Prefers today's date, falls back to any booked lead so the demo
    always has something to brief on.
    """
    today = date.today().isoformat()

    async with httpx.AsyncClient(timeout=15) as client:
        # First try: Viewing Booked + today's date (case-insensitive status match)
        formula = f"AND(SEARCH('viewing booked', LOWER({{Status}})), IS_SAME({{Viewing Date}}, '{today}', 'day'))"
        resp = await client.get(
            f"{BASE_URL}/Leads",
            headers=HEADERS(),
            params={
                "filterByFormula": formula,
                "sort[0][field]": "Viewing Date",
                "sort[0][direction]": "asc",
                "maxRecords": 1,
            },
        )
        data = resp.json()

        if data.get("records"):
            return _clean(data["records"][0]["fields"])

        # Second try: any Viewing Booked lead
        resp = await client.get(
            f"{BASE_URL}/Leads",
            headers=HEADERS(),
            params={
                "filterByFormula": "SEARCH('viewing booked', LOWER({Status}))",
                "sort[0][field]": "Score",
                "sort[0][direction]": "desc",
                "maxRecords": 1,
            },
        )
        data = resp.json()

        if data.get("records"):
            return _clean(data["records"][0]["fields"])

        # Last resort: highest-scoring lead (ensures demo always has someone interesting)
        resp = await client.get(
            f"{BASE_URL}/Leads",
            headers=HEADERS(),
            params={
                "sort[0][field]": "Score",
                "sort[0][direction]": "desc",
                "maxRecords": 1,
            },
        )
        data = resp.json()

        if data.get("records"):
            return _clean(data["records"][0]["fields"])

        # If we still have nothing, Airtable auth is likely wrong
        print("Airtable response:", data)

    return None


def _clean(fields: dict, record_id: str = "") -> dict:
    return {
        "id": record_id,
        "name": fields.get("Name", "Unknown"),
        "contact": fields.get("Contact", ""),
        "phone": fields.get("Phone", ""),
        "platform": fields.get("Platform", ""),
        "property_interest": fields.get("Property Interest", "Not specified"),
        "budget": fields.get("Budget", "Not specified"),
        "intent": fields.get("Intent", ""),
        "urgency": fields.get("Urgency", ""),
        "tag": fields.get("Tag", ""),
        "score": fields.get("Score", 0),
        "message": fields.get("Message", ""),
        "voice_transcript": fields.get("Voice Transcript", ""),
        "status": fields.get("Status", ""),
        "viewing_date": fields.get("Viewing Date", ""),
    }

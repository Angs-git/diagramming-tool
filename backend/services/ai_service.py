from dotenv import load_dotenv
import os
import base64
import json
import httpx
import time
import logging
import re
from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from typing import List, Optional, Tuple

# ----------------- Logging Setup -----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------- Environment Setup -----------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# ----------------- Pydantic Models -----------------
class Shape(BaseModel):
    type: str
    x: Optional[int] = None
    y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    start: Optional[Tuple[int, int]] = None
    end: Optional[Tuple[int, int]] = None

class CleanedDiagram(BaseModel):
    shapes: List[Shape]

# ----------------- AI Service -----------------
async def clean_diagram(image_bytes: bytes) -> dict:
    """
    Analyze a diagram image using Gemini and return structured drawing commands.
    Always returns a validated JSON (CleanedDiagram) if possible.
    """
    try:
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                "Analyze this diagram and return a JSON object "
                                "with a list of shapes (type, coordinates, width/height, "
                                "or start/end points). The output must be pure JSON."
                            )
                        },
                        {"inline_data": {"mime_type": "image/png", "data": b64_image}},
                    ]
                }
            ]
        }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            "models/gemini-2.5-pro:generateContent"
        )

        max_retries = 3
        for attempt in range(max_retries):
            async with httpx.AsyncClient(timeout=30) as client:
                try:
                    logger.info(f"Sending request to Gemini API (attempt {attempt + 1})")
                    resp = await client.post(f"{url}?key={GEMINI_API_KEY}", json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    logger.info("Request successful")

                    # --- Extract Gemini text output ---
                    raw_output = data["candidates"][0]["content"]["parts"][0]["text"]

                    # --- Clean possible ```json ... ``` fences ---
                    clean_text = re.sub(r"```json|```", "", raw_output).strip()

                    try:
                        parsed = json.loads(clean_text)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Response is not valid JSON after cleaning: {e}")
                        return {"error": "Invalid JSON from Gemini", "raw_text": raw_output}

                    # --- Validate & Standardize ---
                    try:
                        cleaned = CleanedDiagram(**parsed)
                        return {"structured_commands": cleaned.dict()}
                    except ValidationError as e:
                        logger.warning(f"Validation failed: {e}")
                        # Return raw parsed dict for debugging
                        return {"error": "Validation failed", "raw_output": parsed}

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 503:
                        logger.warning(f"503 Service Unavailable, retrying in {2**attempt}s...")
                        time.sleep(2**attempt)
                        if attempt == max_retries - 1:
                            return {"error": f"503 Service Unavailable after {max_retries} attempts"}
                    else:
                        logger.error(f"HTTP error: {e}")
                        return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}

                except httpx.RequestException as e:
                    logger.error(f"Network error: {e}")
                    return {"error": f"Network error: {str(e)}"}

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {"error": str(e)}


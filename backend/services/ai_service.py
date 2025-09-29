from dotenv import load_dotenv
import os
import base64
import json
import httpx
import time
import logging
import re   # 👈 ADD THIS

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Verify API key is loaded
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file")

async def clean_diagram(image_bytes: bytes) -> dict:
    """
    Analyze a diagram image and return a JSON object with nodes, edges,
    and alignment suggestions.
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
                                "with nodes, edges, and alignment suggestions."
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

                    # Extract Gemini text output
                    raw_output = data["candidates"][0]["content"]["parts"][0]["text"]

                    # 🔹 Clean possible ```json ... ``` fences
                    clean_text = re.sub(r"```json|```", "", raw_output).strip()

                    try:
                        return json.loads(clean_text)   # ✅ Always return dict if possible
                    except json.JSONDecodeError:
                        logger.warning("Response is not valid JSON after cleaning")
                        return {"raw_text": raw_output}

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 503:
                        logger.warning(f"503 Service Unavailable, retrying in {2**attempt}s...")
                        time.sleep(2**attempt)
                        if attempt == max_retries - 1:
                            logger.error("Max retries reached")
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

"""Text-to-image generation via OpenAI's GPT Image model (used by the recap and preview graphs)."""
import base64
import os
from typing import Optional

from openai import OpenAI

IMAGE_MODEL = os.environ.get("FANTASY_AGENT_OPENAI_IMAGE_MODEL", "gpt-image-2")

API_KEY = os.environ.get("OPENAI_API_KEY")

# size: "1024x1024", "1536x1024" (landscape), "1024x1536" (portrait), or "auto".
# quality: "low" .. "max" or "auto"; higher costs steeply more tokens.


def generate_image(prompt: str, size: Optional[str] = None, quality: Optional[str] = None) -> bytes:
    """Return image bytes for `prompt`; raises if no image data comes back."""
    client = OpenAI(api_key=API_KEY)
    response = client.images.generate(
        model=IMAGE_MODEL, prompt=prompt, size=size or "auto", quality=quality or "high"
    )

    b64 = response.data[0].b64_json
    if not b64:
        raise ValueError("image model response contained no image data")
    return base64.b64decode(b64)

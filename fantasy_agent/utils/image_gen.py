"""Text-to-image generation via Gemini's image model ("Nano Banana"), shared
by any langgraph node that wants a polished graphic instead of a plain-text
or matplotlib reply.
"""
import os
from typing import Optional

from google import genai
from google.genai import types

IMAGE_MODEL = os.environ.get("FANTASY_AGENT_IMAGE_MODEL", "gemini-3-pro-image")

API_KEY = os.environ.get("GOOGLE_API_KEY")

# Supported by ImageConfig.aspect_ratio: "1:1", "2:3", "3:2", "3:4", "4:3",
# "9:16", "16:9", "21:9".


def generate_image(
    prompt: str, aspect_ratio: Optional[str] = None, image_size: Optional[str] = None
) -> bytes:
    """Returns image bytes for `prompt`. Raises if the call fails or the
    response contains no image part. `aspect_ratio` (e.g. "16:9" for
    landscape) and `image_size` ("1K"/"2K"/"4K") are passed through as-is;
    omit either to use the model default."""
    client = genai.Client(api_key=API_KEY)
    config = (
        types.GenerateContentConfig(
            image_config=types.ImageConfig(aspect_ratio=aspect_ratio, image_size=image_size)
        )
        if aspect_ratio or image_size else None
    )
    response = client.models.generate_content(model=IMAGE_MODEL, contents=[prompt], config=config)

    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            return part.inline_data.data

    raise ValueError("image model response contained no image data")

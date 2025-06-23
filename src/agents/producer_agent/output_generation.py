from google.genai import types

from src.agents.utils import gemini_with_structured_output
from src.api.models import PlainText

SYSTEM_PROMPT = """
You are the output node of a chatbot system.

Your tasks:
1. Split the provided text into a sequence of plain text components.
2. Ensure the output contains only plain text—do not include any markdown, bullet points, asterisks, or special formatting.
3. Preserve the original meaning and structure, but present each component as simple, unformatted text.
"""


async def output_generation(content: str) -> list[PlainText] | None:
    return await gemini_with_structured_output(
        model_name="gemini-2.0-flash",
        schema=list[PlainText],
        contents=[types.Content(role="user", parts=[types.Part(text=content)])],
        system_message=SYSTEM_PROMPT,
    )

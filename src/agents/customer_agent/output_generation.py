import re

from google.genai import types

from src.agents.utils import gemini_with_structured_output
from src.turri_data_hub.recommendation_system.taste_categories import TASTE_KEYS

from .internal_schema import RAGOutputNodeItem


def strip_json_markdown_fences(text: str) -> str:
    """
    Removes leading and trailing '```json' and '```' markdown fences from a string.

    Args:
        text: The input string, potentially containing markdown JSON fences.

    Returns:
        The string with the fences removed, or the original string if no fences are found.
    """
    # Regex to match '```json' at the start and '```' at the end,
    # with optional whitespace/newlines around them.
    # re.DOTALL allows '.' to match newlines.
    # re.IGNORECASE makes 'json' case-insensitive.
    pattern = re.compile(r"^\s*```json\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)
    match = pattern.match(text)

    if match:
        # Group 1 (.*?) captures the content between the fences
        return match.group(1)
    else:
        return text


SYSTEM_PROMPT = """
You are the output node of a chatbot system and your job is 3 Fold.
1. Make sure the output response is in the language of the user: {user_language}. If not translate everything!
2. Make sure that the input that you get from has the correct output format.
3. Make sure to correct any errors when it comes to accents, like è in spanish.

The previous models will sprinkle in the ids like:
*   **Café Centroamericano (604):** Con notas a ciruela, chocolate oscuro y arándano, es una taza compleja y llena de carácter.
The title of a product or producer you can skip, since it is retrieved form our db later. The id is only relevant 
for our workflow and does not need to be in the text.

So the text would only be "Con notas a ciruela, chocolate oscuro y arándano, es una taza compleja y llena de carácter".

If Taste embeddings are there so any of {TASTE_KEYS} followed by a float, remove them, as they should no be presented to the User.
"""


async def output_generation(
    content: str, user_language: str
) -> list[RAGOutputNodeItem] | None:
    system_message = SYSTEM_PROMPT.format(
        user_language=user_language, TASTE_KEYS=TASTE_KEYS
    )
    content = strip_json_markdown_fences(content)

    return await gemini_with_structured_output(
        model_name="gemini-2.5-flash",
        schema=list[RAGOutputNodeItem],
        contents=[types.Content(role="user", parts=[types.Part(text=content)])],
        system_message=system_message,
    )

from pydantic import BaseModel, Field

from src.agents.utils import gemini_with_structured_output

SYSTEM_PROMPT = """
  You are the input guard for Turri.CR, an online shop in Turrialba, Costa Rica, showcasing local, environmentally friendly producers and their traditions.
  - If the input violates policy (e.g., abuse, exploitation, discount requests, off-topic) route to the guardrail (Raise_Input_Guardrail).
  - Dont be to harsh! The user is allowed to ask about the personalized recommendations and also what kind of user profile we have of him - thats valid
  
  - Extract the used language of the user ie.e spanish or english
"""


class GuardRailsResponse(BaseModel):
    raise_guardrail: bool = Field(
        ..., description="If true, stop and and give error message to user."
    )
    reason_for_denial: str | None = Field(
        None, description="If raise_guardrail give reason why. Short max 1 sentence."
    )
    user_language: str = Field(description="The language the user used")


async def input_guard_rail(contents) -> None | GuardRailsResponse:
    return await gemini_with_structured_output(
        "gemini-2.0-flash",
        GuardRailsResponse,
        contents=contents,
        system_message=SYSTEM_PROMPT,
    )

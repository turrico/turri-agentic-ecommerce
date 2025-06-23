import sys

sys.path.append(".")
import time
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from loguru import logger
from typing_extensions import override

from .guard_rail import input_guard_rail


class GuardrailAgentWrapper(BaseAgent):
    guard_rail_reponse: str = "I'm sorry, but I can't help with that."
    main_llm_agent: LlmAgent

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, name: str, main_llm_agent: LlmAgent):
        super().__init__(
            name=name,
            main_llm_agent=main_llm_agent,
            sub_agents=[main_llm_agent],
        )

    @override
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        contents = [
            part
            for event in ctx.session.events
            if event.content
            for part in event.content.parts
            if part and event.author == self.name or event.author == "user"
        ]

        if not contents:
            logger.warning(
                f"[{self.name}] No user message found in session history for validation. Allowing."
            )
            # If no user message, just proceed to the main agent
            async for event in self.main_llm_agent.run_async(ctx):
                yield event
            return
        result = await input_guard_rail(contents=contents)
        if result is not None:
            ctx.session.state["user_language"] = result.user_language
            state_changes = {
                "user_language": result.user_language  # Update session state
            }
            actions_with_update = EventActions(state_delta=state_changes)
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                actions=actions_with_update,
                timestamp=time.time(),
            )

        if result is not None and result.raise_guardrail:
            logger.info(
                f"[{self.name}] Guardrail: Input deemed INVALID because of {result.reason_for_denial}"
            )

            # Yield an Event directly from this agent to the user
            yield Event(
                author=self.name,  # The guardrail agent is responding
                invocation_id=ctx.invocation_id,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=self.guard_rail_reponse)],
                ),
                turn_complete=True,  # This marks the end of the turn
            )
            return

        async for event in self.main_llm_agent.run_async(ctx):
            yield event
        return

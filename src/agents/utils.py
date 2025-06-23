import asyncio
from functools import partial
from typing import Any, Optional, Type  # Added Any

import numpy as np
from google import genai
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.genai import types
from loguru import logger
from pydantic import BaseModel

from .settings import settings


def make_numpy_values_serialiable(vals: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively cast numpy bools, ints, and floats to normal types such that they can be serialized.
    vals can be nested.
    """

    def convert(val):
        if isinstance(val, dict):
            return {k: convert(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [convert(v) for v in val]
        elif isinstance(val, np.generic):
            return val.item()
        elif isinstance(val, np.ndarray):
            return val.tolist()
        else:
            return val

    return convert(vals)


async def gemini_with_structured_output(
    model_name: str,
    schema: Type[BaseModel],
    contents,
    system_message,
    temperature=0.00,
) -> BaseModel | None:
    def _gemini_call():
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        config = {
            "system_instruction": system_message,
            "response_mime_type": "application/json",
            "response_schema": schema,
            "temperature": temperature,
        }
        if model_name.startswith("gemini-2.5-flash"):
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

        return client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config),
        )

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(_gemini_call), timeout=settings.GEMINI_TIME_OUT
        )
    except asyncio.TimeoutError:
        # handle timeout here (log, raise, return, etc)
        raise RuntimeError("Gemini API call timed out")

    return response.parsed


async def gemini_only_text(
    model_name: str,
    contents,
    system_message,
    temperature=0.00,
) -> str:
    def _gemini_call():
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        config = {
            "system_instruction": system_message,
            "temperature": temperature,
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        }
        if model_name.startswith("gemini-2.5-flash"):
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

        return client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config),
        )

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(_gemini_call), timeout=settings.GEMINI_TIME_OUT
        )
    except asyncio.TimeoutError:
        # handle timeout here (log, raise, return, etc)
        raise RuntimeError("Gemini API call timed out")

    return response.text


async def gemini_with_tools_single_call(
    model_name: str,
    contents,
    system_message,
    tools: list,
    temperature=0.00,
) -> types.GenerateContentResponse:
    def _gemini_call():
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        config = {
            "system_instruction": system_message,
            "temperature": temperature,
            "tools": tools,
            "automatic_function_calling": types.AutomaticFunctionCallingConfig(
                disable=True
            ),
        }
        if model_name.startswith("gemini-2.5-flash"):
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

        return client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config),
        )

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(_gemini_call), timeout=settings.GEMINI_TIME_OUT
        )
    except asyncio.TimeoutError:
        # handle timeout here (log, raise, return, etc)
        raise RuntimeError("Gemini API call timed out")

    return response


async def gemini_with_tools_automatic_asnyc(
    model_name: str,
    contents,
    system_message,
    tools: list,
    temperature=0.00,
    max_loops=2,
):
    for i in range(max_loops):
        logger.debug("Function step:")
        res = await gemini_with_tools_single_call(
            model_name=model_name,
            contents=contents,
            system_message=system_message,
            tools=tools,
            temperature=temperature,
        )

        if not res.function_calls:
            return res.text

        logger.debug(f"Function Calls: {res.function_calls}")

        for call in res.function_calls:
            logger.debug(f"Calling {call.name} with {call.args}")

            func = next(
                i
                for i in tools
                if (
                    (hasattr(i, "__name__") and i.__name__ == call.name)
                    or (isinstance(i, partial) and i.func.__name__ == call.name)
                )
            )

            res = await func(**call.args)
            contents.append(
                types.Content(
                    parts=[
                        types.Part(
                            function_response={
                                "name": call.name,
                                "id": getattr(call, "id", None),
                                "response": {"output": res},
                                "will_continue": False,
                                "scheduling": None,
                            }
                        )
                    ]
                )
            )

    return await gemini_only_text(
        model_name=model_name,
        contents=contents,
        system_message=system_message,
        temperature=temperature,
    )


async def gemini_with_code_execution(
    model_name: str,
    contents,
    system_message,
    temperature=0.00,
) -> str:
    def _gemini_call():
        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        config = {
            "system_instruction": system_message,
            "temperature": temperature,
            "tools": [types.Tool(code_execution=types.ToolCodeExecution)],
        }
        if model_name.startswith("gemini-2.5-flash"):
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

        return client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config),
        )

    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(_gemini_call), timeout=settings.GEMINI_TIME_OUT
        )
    except asyncio.TimeoutError:
        # handle timeout here (log, raise, return, etc)
        raise RuntimeError("Gemini API call timed out")

    return response


def format_tool_args(tool_name: str, *args, **kwargs) -> str:
    """
    Formats tool call arguments for logging in a nice way.
    Example: 🛠️ [TOOL] tool_name called with: Arg1=val1, Arg2=val2
    """
    arg_strs = []
    # Positional args (rare, but just in case)
    for i, arg in enumerate(args):
        arg_strs.append(f"arg{i + 1}={repr(arg)}")
    # Keyword args
    for k, v in kwargs.items():
        # For tool_context, try to extract user id if present
        if k == "tool_context" and hasattr(v, "state"):
            user_id = v.state.get("user:user_id") if hasattr(v, "state") else None
            arg_strs.append(f"user_id={user_id}")
        else:
            arg_strs.append(f"{k}={repr(v)}")
    joined = ", ".join(arg_strs)
    return f"\U0001f6e0 [TOOL] {tool_name} called with: {joined}"


def agent_log_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Logs the agent name and the most recent user message before execution.
    Attach as before_agent_callback to any ADK agent.
    """
    agent_name = getattr(callback_context, "agent_name", "unknown")
    msgs = getattr(callback_context, "invocation_context", None)
    last_msg = None
    if msgs and hasattr(msgs, "messages") and msgs.messages:
        last = msgs.messages[-1]
        if hasattr(last, "parts") and last.parts and hasattr(last.parts[0], "text"):
            last_msg = last.parts[0].text
    if last_msg:
        logger.info(
            f"\U0001f6e0 [AGENT] {agent_name} starting. Last user message: {last_msg}"
        )
    else:
        logger.info(f"\U0001f6e0 [AGENT] {agent_name} starting. ")
    return None


def before_model_logging_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> None:
    """
    Logs the agent name and a readable prefix of the LLM request before the model call.
    Attach as before_model_callback to any ADK agent.
    """
    agent_name = getattr(callback_context, "agent_name", "unknown")
    # serialize all message texts into one string
    full_text = "".join(
        part.text
        for msg in llm_request.contents
        for part in msg.parts
        if hasattr(part, "text") and part.text
    )
    prefix = full_text[-100:]
    # logger.info(f"\U0001f916 [LLM] {agent_name} Model Call: {prefix!r}")
    return None

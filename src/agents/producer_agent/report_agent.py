"""Still experimental"""

import sys

sys.path.append(".")
import asyncio
import json
import logging
import os
from datetime import datetime

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.models import LlmRequest
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import ToolContext
from google.genai import types
from loguru import logger

from src.agents.producer_agent.generate_report import generate_report
from src.agents.producer_agent.tools import (
    get_orders_of_product,
    get_producer_webiste_views,
    get_producer_website_users_counts_by_region,
    get_product_website_users_counts_by_region,
    get_product_website_views,
    get_products,
    get_customer_profiles,
)
from src.agents.utils import agent_log_callback, before_model_logging_callback


def add_current_report_state(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> None:
    llm_request.contents.append(
        types.Content(
            role="model",
            parts=[
                types.Part(
                    text=f"Current Report State: {json.dumps(callback_context.state['report'])}"
                )
            ],
        )
    )
    return None


class _NoFunctionCallWarning(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if "there are non-text parts in the response:" in message:
            return False
        else:
            return True


logging.getLogger("google_genai.types").addFilter(_NoFunctionCallWarning())

GEMINI_MODEL = "gemini-2.0-flash"


stats_agent = Agent(
    name="stats_agent",
    model=GEMINI_MODEL,
    code_executor=BuiltInCodeExecutor(),
    instruction="""You are a data science assistant.
    Your task is to receive a user request and a JSON dataset.
    Use pandas and numpy to generate statistics .
    """,
    description="An agent that performs data analysis for business data.",
    before_agent_callback=agent_log_callback,
    before_model_callback=before_model_logging_callback,
)


def add_report_section(
    heading: str, body: str, img_prompt: str, tool_context: ToolContext
):
    """
    Add a new section to the report planning state.

    Args:
        heading (str): The title or heading for this section of the report.
        body (str): A brief description of what this section is about. This text will be shown under any associated image.
        img_prompt (str): A detailed prompt for the plotting agent if a plot is aplicable for this section; otherwise, an empty string.
        tool_context (ToolContext): The tool context containing the current state, including the report.

    Side Effects:
        Modifies the 'report' dictionary in the tool_context state by adding a new section at the next available position.
    """
    logger.info("add report")

    report = tool_context.state["report"].copy()
    item = {"heading": heading, "body": body, "img_prompt": img_prompt}
    pos = len(report)
    report[pos] = item

    tool_context.state["report"] = report


def delete_report_section(pos: int, tool_context: ToolContext):
    """
    Remove a section from the report planning state by its position.

    Args:
        pos (int): The position (index) of the section to delete.
        tool_context (ToolContext): The tool context containing the current state, including the report.

    Side Effects:
        Deletes the specified section from the 'report' dictionary in the tool_context state.
        Logs a warning if the specified position does not exist.
    """
    logger.info(f"delte report {pos} ")

    report = tool_context.state["report"].copy()

    if pos not in report:
        logger.warning(f"Halucinated pos {pos} when deleting")
        return

    # 2. Modify the copy
    del report[pos]

    # 3. Reassign the modified copy back to the state
    tool_context.state["report"] = report


def spot_planning_start_generating_report(tool_context: ToolContext):
    """
    Mark the planning stage as complete and trigger the start of report generation.

    Args:
        tool_context (ToolContext): The tool context containing the current state.

    Side Effects:
        Sets the 'start_generating' flag to True in the tool_context state to indicate that report generation should begin.
    """
    logger.info("start generating report")
    tool_context.state["start_generating"] = True


report_agent = Agent(
    name="report_agent",
    model=GEMINI_MODEL,
    instruction=f"""We have a online platform were we sell products of Costa Rican Producers. 
    You are a assistant for the producers to generate reports.  Today is {datetime.now()}.
    More specifically your role is helping the producer plan what kind of report he wants. 
    Use your tools to provide the user with a list of data that you can include in the reports. 
    
    Importantly you can add and delete report sections.
    
    Importantly use spot_planning_start_generating_report if the user wants the report
    """,
    description="You are agent that help to plan a business report",
    tools=[
        get_products,
        get_producer_webiste_views,
        get_producer_website_users_counts_by_region,
        get_product_website_users_counts_by_region,
        get_product_website_views,
        get_orders_of_product,
        add_report_section,
        delete_report_section,
        get_customer_profiles,
        spot_planning_start_generating_report,
    ],
    before_model_callback=[add_current_report_state, before_model_logging_callback],
    before_agent_callback=agent_log_callback,
)


async def main():
    """Sets up the agent and runs the conversational loop."""
    if not os.getenv("GOOGLE_API_KEY"):
        print("ERROR: GOOGLE_API_KEY environment variable not set.")
        return

    session_service = InMemorySessionService()
    app_name = "producer_agent_app"
    user_id = "producer_001"
    session_id = "session_12345"

    # Set the producer_id in the initial session state
    initial_state = {"producer_id": 728, "report": {}}
    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state=initial_state,
    )

    runner = Runner(
        agent=report_agent,
        app_name=app_name,
        session_service=session_service,
        artifact_service=InMemoryArtifactService(),
    )

    print("Producer Agent is ready. Type 'quit' to exit.")
    print(f"Session started for producer_id: {initial_state['producer_id']}")

    messages = [
        (
            "Write a report where you you analize the where my users are from and what is thy typical user profile of mine"
            "More excactly I would like to have a bar plot of customers by countries. I know that you dont ahve that infortmaiton bat can you agregate it?"
            "Make sure to specify that the regions should be countries in the plot! "
        ),
        "Looks great, start to generate it!",
    ]

    for query in messages:
        try:
            print(f">>> You: {query}")
            content = types.Content(role="user", parts=[types.Part(text=query)])
            final_response = "Sorry, I could not process that."

            async for event in runner.run_async(
                user_id=user_id, session_id=session_id, new_message=content
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    final_response = event.content.parts[0].text

            print(f"<<< Agent: {final_response}")

            session = await session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
            )
            logger.info(f"Report: {session.state['report']}")

            if session.state.get("start_generating", False):
                logger.info("Generating Report")
                pdf_bytes = await generate_report(
                    session.state["report"], session.state["producer_id"]
                )
                with open("example.pdf", "wb") as f:
                    f.write(pdf_bytes)
                logger.success("Report not at example.pdf")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting agent session. Goodbye!")
            break
        except Exception as e:
            logger.exception(f"An error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())

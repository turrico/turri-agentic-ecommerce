import logging
from datetime import datetime

from google.adk.agents import Agent
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.tools import agent_tool

from src.agents.producer_agent.tools import (
    get_customer_profiles,
    get_orders_of_product,
    get_producer_webiste_views,
    get_producer_website_users_counts_by_region,
    get_product_website_users_counts_by_region,
    get_product_website_views,
    get_products,
)
from src.agents.utils import agent_log_callback, before_model_logging_callback


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


data_gathering_agent = Agent(
    name="data_gathering_agent",
    model=GEMINI_MODEL,
    tools=[
        get_producer_webiste_views,
        get_producer_website_users_counts_by_region,
        get_product_website_users_counts_by_region,
        get_product_website_views,
        get_orders_of_product,
        get_products,
        get_customer_profiles,
    ],
    instruction="""You are an agent that gathers business data for the producer.
    Use your tools to fetch product, order, or analytics data as needed.
    Get all relevant data, most importantly product ids of the respoective prodiucts""",
    description="An agent that fetches data from backend systems for business analysis report seciton.",
    output_key="data_gathering_agent",
    before_agent_callback=agent_log_callback,
    before_model_callback=before_model_logging_callback,
)


conv_and_planning_agent = Agent(
    name="conv_and_planning_agent",
    model=GEMINI_MODEL,
    instruction=f"""We have a online platform were we sell products of Costa Rican Producers. 
    You are a assistant for the producers to generate reports.  Today is {datetime.now()}.
    More specifically your role is helping the producer get answers to business questions
    """,
    tools=[
        get_products,
        agent_tool.AgentTool(data_gathering_agent),
    ],
    sub_agents=[data_gathering_agent],
    before_agent_callback=agent_log_callback,
    before_model_callback=before_model_logging_callback,
)

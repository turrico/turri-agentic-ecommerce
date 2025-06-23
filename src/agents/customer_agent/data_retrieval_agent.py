from google.adk.agents import Agent

from src.agents.utils import agent_log_callback, before_model_logging_callback

from .tools import (
    get_products_of_producer_tool,
    rag_fetch_producers_tool,
    rag_fetch_products_tool,
)


def make_data_retrieval_agent() -> Agent:
    return Agent(
        name="data_retrieval_agent",
        model="gemini-2.0-flash",
        description="Retrieves Products and Producer offerings of our Online Shop",
        instruction=(
            "You are part of a customer onboarding system of Turri.CR, an online shop in Turrialba, Costa Rica. "
            "It's your job to retrieve the relevant information. Importantly, when returning a product or producer, "
            "the most important information is the producer or product id, so we can use it later. "
            "Additionally, the taste_embeddings are really important and should always be included, as well as the content of the Product or Producer. "
        ),
        tools=[
            rag_fetch_products_tool,
            rag_fetch_producers_tool,
            get_products_of_producer_tool,
        ],
        before_agent_callback=agent_log_callback,
        before_model_callback=before_model_logging_callback,
    )

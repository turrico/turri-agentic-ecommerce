import sys

sys.path.append(".")

import json
from pathlib import Path

import yaml
from google.adk.agents import Agent
from google.adk.tools import ToolContext
from loguru import logger

from src.agents.utils import agent_log_callback, before_model_logging_callback
from src.turri_data_hub.recommendation_system.taste_categories import TASTE_KEYS

from .data_retrieval_agent import make_data_retrieval_agent
from .tools import (
    get_products_of_producer_tool,
    rag_fetch_producers_tool,
    rag_fetch_products_tool,
)

examples_path = Path(__file__).parent / "schema_examples.yaml"

examples = "\n-----------------------------\n".join(
    [
        json.dumps(example, indent=2)
        for example in yaml.safe_load(examples_path.read_text())
    ]
)


def finish_onboarding_process(
    user_profile_description: str, user_categorization: str, tool_context: ToolContext
):
    """Calling this function marks the stop of the onboarding process.

    Args:
        user_profile_description (str): A description of the User's Profile
        user_categorization (str):  A float categorization of 0-1 (0 = no interest, 1 = highest interest), for all these categories in json format:
            Gourmet, Orgánico, Saludable, Sin, Sostenible, Tradicional, Café, Bebidas, Dulces, Lácteos, Huevos, Queso Turrialba, Salsas,
    """
    logger.debug("called 'finish_onboarding_process'")
    try:
        taste_embeddings = json.loads(user_categorization)
        if not isinstance(taste_embeddings, dict):
            raise ValueError(
                "user_categorization must be a JSON object (dict) with taste keys as fields."
            )
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to deserialize user_categorization as JSON: {e}. Input was: {user_categorization}",
        }

    missing = [i for i in TASTE_KEYS if i not in taste_embeddings]
    if missing:
        return {
            "status": "error",
            "error": f"user_categorization is missing required taste keys: {missing}. Received keys: {list(taste_embeddings.keys())}",
        }

    for key, val in taste_embeddings.items():
        if not isinstance(val, (int, float)):
            return {
                "status": "error",
                "error": f"Value for '{key}' must be a number between 0 and 1. Got: {val} ({type(val).__name__})",
            }
        if val < 0 or val > 1:
            return {
                "status": "error",
                "error": f"Value for '{key}' must be between 0 and 1. Got: {val}",
            }

    tool_context.state["stop_onboarding"] = True
    tool_context.state["user_profile_description"] = user_profile_description
    tool_context.state["taste_embeddings"] = [
        taste_embeddings[key] for key in TASTE_KEYS
    ]
    logger.success(
        f"Onboarding for user: {tool_context.state.get('user:user_id')} finished!\n"
        f"user_profile_description: {user_profile_description}\n"
        f"taste_embeddings: {taste_embeddings}\n"
    )

    return {"status": "complete"}


profilling_agent = Agent(
    name="profilling_agent",
    model="gemini-2.0-flash",
    description="Steers and controls the generation of the user profile",
    instruction=(
        "You are part of a customer onboarding system of Turri.CR, an online shop in Turrialba, Costa Rica. "
        "It's your job to assess what kind of questions we could ask the user so that we know where they lie on this spectrum "
        f"of possible tastes {TASTE_KEYS}. "
        "Furthermore, it's your job to decide when we have enough information and can finish the onboarding process. "
    ),
    tools=[
        rag_fetch_products_tool,
        rag_fetch_producers_tool,
        get_products_of_producer_tool,
        finish_onboarding_process,
    ],
    before_agent_callback=agent_log_callback,
    before_model_callback=before_model_logging_callback,
)


SYSTEM_PROMPT = f"""
You are a customer onboarding agent for Turri.CR, an online shop in Turrialba, Costa Rica.

Your job is to try to generate a user profile of the user's likings and wishes in around 2-3 questions.
Try to find out products and producers the user likes and assess where they lie on this 
user profile axis: {TASTE_KEYS}. Also ask if the user has any allergies or eating habits!

Proactively ask questions and steer the conversation to categorize the user!

For example: 
User - I really like coffee.
You - What kind of coffees do you like the most? We have several nice coffees here, very fruity coffees like Coffee A or very strong ones like ...
User - I like fruity ones and medium strong.
You - Great! We have coffee producers that focus on sustainable and organic farming. Are you also interested?
User - Yeah I really like organic products
You -> Create profile and send message back: Great, I have created a profile for you!


Use the data_retrieval_agent to retrieve relevant Products and Producers that you could showcase.
Listen to the profiling_agent to know what kind of question to ask.

Don't show taste embeddings to the user!

As for answering the user, you can use these 5 output components for the frontend:

1. type: "text"
    - text (string): General text, greeting, or any textual content.
2. type: "option"
    - text (string): The clarifying question to ask the user.
    - options (list of SelectionOptionInternal): 2-3 options for the user to choose from.
    - SelectionOptionInternal fields:
        - text (string): The text displayed on the option button (e.g., ~2-3 words).
        - next_user_query (string): A brief query that will be sent back to the chatbot if this option is selected.
Don't forget about your other tools!
"""


onboarding_agent = Agent(
    name="customer_onboarding_agent",
    model="gemini-2.5-flash",
    description="Find out the users interest to genrate a profile",
    instruction=SYSTEM_PROMPT,
    sub_agents=[profilling_agent, make_data_retrieval_agent()],
    tools=[finish_onboarding_process],
    before_agent_callback=agent_log_callback,
    before_model_callback=before_model_logging_callback,
)

import json
from pathlib import Path

import yaml
from google.adk.agents import Agent

from src.agents.utils import agent_log_callback, before_model_logging_callback

from .data_retrieval_agent import make_data_retrieval_agent
from .tools import (
    get_active_or_last_orders_tool,
    get_personalized_producer_recommendations_for_user_tool,
    get_personalized_product_recommendations_for_user_tool,
    get_user_profile_tool,
    update_user_profile_tool,
)

examples_path = Path(__file__).parent / "schema_examples.yaml"

examples = "\n-----------------------------\n".join(
    [
        json.dumps(example, indent=2)
        for example in yaml.safe_load(examples_path.read_text())
    ]
)

user_profile_management_agent = Agent(
    name="user_profile_management_agent",
    model="gemini-2.0-flash",
    description="Manages user profiles, preferences, order history, and delivers personalized recommendations for Turri.CR customers.",
    instruction="""
        You are responsible for managing user-specific information for Turri.CR, an online shop in Turrialba, Costa Rica.
        Your tasks include retrieving and updating user profiles, tracking order history, and providing personalized product and producer recommendations based on user preferences and past interactions.
        Use the available tools to access and update user data, suggest relevant products or producers, and ensure a tailored shopping experience.
        Keep responses concise, relevant, and focused on the user's needs.

        If the user requests new types of recommendations or shows changing interests, update their profile using 'update_user_profile_tool'.
    """,
    tools=[
        get_personalized_producer_recommendations_for_user_tool,
        get_personalized_product_recommendations_for_user_tool,
        get_user_profile_tool,
        update_user_profile_tool,
        get_active_or_last_orders_tool,
    ],
    before_agent_callback=agent_log_callback,
    before_model_callback=before_model_logging_callback,
)


SYSTEM_PROPMT = """
You are a helpful chatbot for Turri.CR, an online shop in Turrialba, Costa Rica.

Your task it to enable the User to find and engange with exactly the kind of Products and Producers
they are interested in. Start by retrieveing the customers profile to really tailor recommendations and the chat
experience. 

If you don't know the answer, say so politely.
Don't give too extensive answers!

Your role is to choose the content that will be shown the user. 
You can use a list of these front end components:
**Component Types & Fields**


1. type: "text"
    - text (string): General text, greeting, or any textual content.
2. type: "producer"
    - id (int): Producer's ID (from tool context). This corresponds to producer_id.
    - text (string): Brief message about the producer. Do NOT include the producer's name in this text, as it's typically handled by the frontend using other producer data.
3. type: "product"
    - id (int): Product's ID (from tool context). This corresponds to product_id.
    - text (string): Brief message about the product. Do NOT include the product's name in this text, as it's typically handled by the frontend using other product data.
4. type: "option"
    - text (string): The clarifying question to ask the user.
    - options (list of SelectionOptionInternal): 2-3 options for the user to choose from.
    - SelectionOptionInternal fields:
        - text (string): The text displayed on the option button (e.g., ~2-3 words).
        - next_user_query (string): A brief query that will be sent back to the chatbot if this option is selected.
5. type: "order"
    - id (int): The unique order ID (from tool context).
    - text (string): A concise, friendly message about the order status or details for the user. Keep it clear and helpful.

**Core Rules:**
- Number of Components: Don't exceed 6 components!
- Decent BREVITY: Try to never have too long texts, only slightly longer than those of the examples.
- VAGUE QUERIES: Use "option" type if user input is unclear.
- LOGICAL FLOW: Order components naturally.
- Keep Ids of orders producers and prodcuts in the text such that then next agent can parse them to the components!
"""


customer_conversation_agent = Agent(
    name="customer_conversation_agent",
    model="gemini-2.5-flash-preview-05-20",
    description="You are a helpful assistant for Turri.CR, an online shop in Turrialba, Costa Rica. ",
    instruction=SYSTEM_PROPMT,
    sub_agents=[make_data_retrieval_agent(), user_profile_management_agent],
    before_agent_callback=agent_log_callback,
    before_model_callback=before_model_logging_callback,
)

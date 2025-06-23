from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from src.agents.producer_agent.conversation_agent import conv_and_planning_agent
from src.turri_data_hub.settings import database_settings
from src.api.models import PlainText

from .output_generation import output_generation

load_dotenv()

session_service = DatabaseSessionService(
    db_url=database_settings.get_postgres_dsn(driver_name="psycopg2")
)

APP_NAME = "producer_agent"

producer_runner = Runner(
    agent=conv_and_planning_agent, app_name=APP_NAME, session_service=session_service
)


async def get_producer_conversation_response(
    producer_id: int, session_id: str, message: str, new_session: bool
) -> list[PlainText]:
    if new_session:
        initial_state = {"producer_id": int(producer_id)}
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=str(producer_id),
            session_id=str(session_id),
            state=initial_state,
        )

    content = types.Content(role="user", parts=[types.Part(text=message)])

    final_response = ""
    async for event in producer_runner.run_async(
        user_id=str(producer_id), session_id=session_id, new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text
            break

    return await output_generation(final_response)

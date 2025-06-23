from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from src.agents.customer_agent.agent import GuardrailAgentWrapper
from src.turri_data_hub.settings import database_settings
from src.api.models import FrontEndResponse

from .converstation_agent import customer_conversation_agent
from .internal_schema import RAGOutputNodeItem
from .oboarding_agent import onboarding_agent
from .output_generation import output_generation
from .response_conversion import convert_response_to_front_end_components

load_dotenv()

wrapped_conversation_agent = GuardrailAgentWrapper(
    "customer_agent", main_llm_agent=customer_conversation_agent
)


wrapped_onboarding_agent = GuardrailAgentWrapper(
    "onboarding_agent", main_llm_agent=onboarding_agent
)


session_service = DatabaseSessionService(
    db_url=database_settings.get_postgres_dsn(driver_name="psycopg2")
)

APP_NAME = "customer_agent"

normal_runner = Runner(
    agent=wrapped_conversation_agent, app_name=APP_NAME, session_service=session_service
)

onboarding_runner = Runner(
    agent=wrapped_onboarding_agent, app_name=APP_NAME, session_service=session_service
)


async def get_normal_conversation_response(
    user_id: int, session_id: str, message: str, new_session: bool
) -> FrontEndResponse:
    if new_session:
        initial_state = {"user:user_id": int(user_id)}
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=str(user_id),
            session_id=str(session_id),
            state=initial_state,
        )

    content = types.Content(role="user", parts=[types.Part(text=message)])

    final_response = ""
    async for event in normal_runner.run_async(
        user_id=str(user_id), session_id=session_id, new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text
            break

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=str(user_id), session_id=str(session_id)
    )
    user_language = session.state.get("user_language", "espanol")

    if final_response == wrapped_conversation_agent.guard_rail_reponse:
        ouput_result = [
            RAGOutputNodeItem(
                type="text", text=wrapped_conversation_agent.guard_rail_reponse
            )
        ]
    else:
        ouput_result = await output_generation(final_response, user_language)

    response = ouput_result or [RAGOutputNodeItem(text="Ooops, something wen`t wrong.")]

    return await convert_response_to_front_end_components(
        response=response, user_id=user_id
    )


async def get_onboarding_conversation_response(
    user_id: int, session_id: str, message: str, new_session: bool
) -> tuple[FrontEndResponse, dict]:
    if new_session:
        initial_state = {"user:user_id": int(user_id)}
        await session_service.create_session(
            app_name=APP_NAME,
            user_id=str(user_id),
            session_id=str(session_id),
            state=initial_state,
        )

    content = types.Content(role="user", parts=[types.Part(text=message)])

    final_response = ""
    async for event in onboarding_runner.run_async(
        user_id=str(user_id), session_id=session_id, new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_response = event.content.parts[0].text
            break

    session = await session_service.get_session(
        app_name=APP_NAME, user_id=str(user_id), session_id=str(session_id)
    )
    user_language = session.state.get("user_language", "espanol")

    ouput_result = await output_generation(final_response, user_language)

    response = ouput_result or [RAGOutputNodeItem(text="Ooops, something wen`t wrong.")]

    formatted_msg = await convert_response_to_front_end_components(
        response=response, user_id=user_id
    )

    return formatted_msg, session.state

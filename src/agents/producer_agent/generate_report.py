import json
from functools import partial

from google.genai import types
from loguru import logger

from src.agents.producer_agent.tools import (
    get_orders_of_product,
    get_producer_webiste_views,
    get_producer_website_users_counts_by_region,
    get_product_website_users_counts_by_region,
    get_product_website_views,
    get_products,
    get_customer_profiles,
)
from src.agents.utils import (
    gemini_only_text,
    gemini_with_code_execution,
    gemini_with_tools_automatic_asnyc,
)
from src.general import colors
from src.general.reports import ReportSection, generate_report_pdf_bytes

DATA_RETRIEVAL_SYSTEM_MESSAGE: str = (
    "We have a website called turri.cr where we sell local products from Costa Rica.\n"
    "You are assisting in retrieving relevant data for writing business reports for our producers.\n"
    "Given a certain plan of sections for the report, retrieve as much relevant information as possible."
)

REPORT_WRITING_SYSTEM_MESSAGE: str = (
    "We have a website called turri.cr where we sell local products from Costa Rica.\n"
    "You will receive instructions for a report section as well as data, and you will write a report for our producer based on that.\n"
    "Importantly, return only the report—no extra text before or after!\n"
    "All currencies are in Colones."
    "Don't return the Title again. Use very limited markdown."
    "If you do listings only do enumerations so 1. 2. and no - or *"
)

PLOTTING_AGENT_SYSTEM_MESSAGE: str = (
    "We have a website called turri.cr where we sell local products from Costa Rica.\n"
    "You will receive instructions and data to create a matplotlib plot.\n"
    "Only return a PNG image.\n"
    "Try to generate useful titles and axis descriptions.\n"
    "All currencies are in Colones."
    f"When you can use these colors to plot: {colors}"
)


async def create_section(
    section: dict[str, str], producer_information: str, dummy_tool_context
) -> ReportSection:
    data_prompt = (
        f"Retrieve all relevant data for this section: {json.dumps(section, indent=2)}"
        f"General information about the Producer: {producer_information}"
    )

    data = await gemini_with_tools_automatic_asnyc(
        "gemini-2.5-flash",
        contents=[types.Content(role="user", parts=[types.Part(text=data_prompt)])],
        system_message=DATA_RETRIEVAL_SYSTEM_MESSAGE,
        tools=[
            get_orders_of_product,
            partial(get_producer_webiste_views, tool_context=dummy_tool_context),
            partial(
                get_producer_website_users_counts_by_region,
                tool_context=dummy_tool_context,
            ),
            partial(
                get_customer_profiles,
                tool_context=dummy_tool_context,
            ),
            get_product_website_users_counts_by_region,
            get_product_website_views,
        ],
    )
    logger.debug(f"Data reponse: {data}")

    report_prompt = f"The instuctions for the report: {json.dumps(section, indent=2)}. Relevant Data: {data}"
    report_text = await gemini_only_text(
        "gemini-2.0-flash",
        contents=[types.Content(role="user", parts=[types.Part(text=report_prompt)])],
        system_message=REPORT_WRITING_SYSTEM_MESSAGE,
        temperature=1.0,
    )
    logger.debug(f"Report Text: {report_text}")

    if not section["img_prompt"]:
        return ReportSection(
            heading=section["heading"], main_body_text=report_text, png_img=None
        )

    logger.debug("Trying to plot")
    plot_prompt = f"The instuctions for the plot: {json.dumps(section, indent=2)}. Relevant Data: {data}"

    res = await gemini_with_code_execution(
        "gemini-2.5-flash",
        contents=[types.Content(role="user", parts=[types.Part(text=plot_prompt)])],
        system_message=PLOTTING_AGENT_SYSTEM_MESSAGE,
    )

    png_bytes = None
    for part in reversed(res.candidates[0].content.parts):
        if part.inline_data and part.inline_data.mime_type == "image/png":
            png_bytes = part.inline_data.data

    if png_bytes is None:
        logger.debug(f"No img found in: {res}")

    return ReportSection(
        heading=section["heading"], main_body_text=report_text, png_img=png_bytes
    )


async def generate_report(plan: dict[int, dict[str, str]], producer_id: int) -> bytes:
    class Dummy:
        pass

    dummy_tool_context = Dummy()
    dummy_tool_context.state = {"producer_id": producer_id}

    producer_information = json.dumps(
        await get_products(dummy_tool_context), indent=2, default=str
    )

    results: list[ReportSection] = []
    for section in plan.values():
        logger.info(f"Section: {section}")

        res = await create_section(section, producer_information, dummy_tool_context)
        results.append(res)

    # return results
    return generate_report_pdf_bytes(results)

from io import BytesIO

from google.genai import types
from loguru import logger
from PIL import Image

from src.agents.utils import format_tool_args, gemini_with_code_execution
from src.general import colors


async def generate_plot(plot_instructions_including_data: str):
    """
    Generates a matplotlib plot based on the provided instructions and data,
    and displays the resulting image to the user.

    Args:
        plot_instructions_including_data (str): A detailed description including data and instructions
            for the plot to be generated (e.g., plot type, titles, axis labels, colors, etc.).

    Returns:
        dict: A status dictionary indicating success or error details.
    """
    logger.info(
        format_tool_args(
            "generate_plot",
            plot_instructions_including_data=plot_instructions_including_data,
        )
    )
    PLOTTING_AGENT_SYSTEM_MESSAGE: str = (
        "We have a website called turri.cr where we sell local products from Costa Rica.\n"
        "You will receive instructions and data to create a matplotlib plot.\n"
        "Only return a PNG image.\n"
        "Try to generate useful titles and axis descriptions.\n"
        "All currencies are in Colones.\n"
        f"When you can use these colors to plot: {colors}"
    )

    try:
        res = await gemini_with_code_execution(
            "gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=plot_instructions_including_data)],
                )
            ],
            system_message=PLOTTING_AGENT_SYSTEM_MESSAGE,
        )

        png_bytes = None
        for part in reversed(res.candidates[0].content.parts):
            if part.inline_data and part.inline_data.mime_type == "image/png":
                png_bytes = part.inline_data.data

        if png_bytes is None:
            logger.debug(f"No image found in: {res}")
            return {"status": "error", "error_message": "No image found in response."}

        # Show PNG image to user
        img = Image.open(BytesIO(png_bytes))
        img.show()

        return {"status": "success", "message": "Plot shown to user"}

    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] generate_plot error: {e}")
        return {"status": "error", "error_message": str(e)}

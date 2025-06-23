import asyncio

from google import genai
from google.genai import types

from .settings import database_settings

EMBEDDING_DIM = 768


async def compute_embeddings(contents: list[str]) -> list[list[float]]:
    def sync_func():
        client = genai.Client(api_key=database_settings.GOOGLE_API_KEY)
        return client.models.embed_content(
            model=database_settings.embedding_model,
            contents=contents,
            config=types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY", output_dimensionality=EMBEDDING_DIM
            ),
        )

    result = await asyncio.to_thread(sync_func)

    return [emb.values for emb in result.embeddings]

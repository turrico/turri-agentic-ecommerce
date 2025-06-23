from loguru import logger
from tqdm import tqdm

from src.turri_data_hub.db import TurriDB
from src.turri_data_hub.embedding import compute_embeddings
from src.turri_data_hub.woocommerce.models import (
    Producer,
)

from ...recommendation_system.taste_categories import TASTE_KEYS
from .utils import fetch_list, fetch_single, get_text


async def generate_producer(data: dict, db: TurriDB) -> None:
    img = None
    try:
        img = fetch_single(
            data["_links"]["wp:attachment"][0]["href"],
            lambda x: x[0]["media_details"]["sizes"]["thumbnail"]["source_url"],
        )
    except Exception:
        logger.debug("Could not fetch image")
        pass
    if data["status"] != "publish":
        logger.info(f"unkown status '{data['status']}'")

    embeddings = await compute_embeddings(
        [get_text(data["content"]["rendered"], data["excerpt"]["rendered"])]
    )

    producer = Producer(
        id=data["id"],
        link=data["link"],
        title=data["title"]["rendered"],
        content=data["content"]["rendered"],
        excerpt=data["excerpt"]["rendered"],
        slug=data["slug"],
        img_url=img,
        embedding=embeddings[0],
        taste_embedding=[0] * len(TASTE_KEYS),
    )
    await db.save(producer)


async def fetch_generate_and_save_producers(db: TurriDB, per_page=50):
    producers = fetch_list(
        url="/wp-json/wp/v2/productor",
        per_page=per_page,
    )

    for producer in tqdm(producers):
        try:
            await generate_producer(producer, db)
        except Exception as e:
            logger.error(
                f"Error processing producer {producer.get('id', 'unknown')}: {e}"
            )

from loguru import logger
from sqlalchemy.orm import selectinload

from src.turri_data_hub.embedding import compute_embeddings
from src.turri_data_hub.woocommerce.models import Producer, Product

from ...db import db
from ...utils import format_tool_args, make_numpy_values_serialiable
from .utils import _products_to_dict, dump_producer


async def rag_fetch_producers(query: str) -> dict:
    """Fetches producers from the database using a RAG (Retrieval-Augmented Generation) approach.

    Use this tool when you need a list of producers most relevant to the given query.

    Args:
        query (str): The search query to find relevant producers.

    Returns:
        dict: {'status': 'success', 'producers': [producer_dicts]} on success,
              {'status': 'error', 'error_message': str} on failure.
    """
    logger.info(format_tool_args("rag_fetch_producers", query=query))

    try:
        embeddings = await compute_embeddings([query])

        producers: list[Producer] = await db.query_table(
            Producer, order_by=[Producer.embedding.l2_distance(embeddings[0])], limit=5
        )
        result = {
            "status": "success",
            "producers": [dump_producer(p) for p in producers],
        }
        return make_numpy_values_serialiable(result)
    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] rag_fetch_producers error: {e}")
        return {"status": "error", "error_message": str(e)}


async def get_products_of_producer(producer_id: int) -> dict:
    """Fetches products from the database using a RAG (Retrieval-Augmented Generation) approach.

    Use this tool when you need a list of products most relevant to the given query.

    Args:
        query (str): The search query to find relevant products.

    Returns:
        dict: {'status': 'success', 'products': [producer_dicts]} on success,
              {'status': 'error', 'error_message': str} on failure.
    """
    logger.info(format_tool_args("get_products_of_producer", producer_id=producer_id))

    try:
        products = await db.query_table(
            Product,
            where_clauses=[
                Product.producer_id == producer_id,
                Product.catalog_visibility == "visible",
                Product.status == "publish",
            ],
            options=[selectinload(Product.categories), selectinload(Product.tags)],
        )

        result = {
            "status": "success",
            "products": _products_to_dict(products),
        }
        return make_numpy_values_serialiable(result)
    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] get_products_of_producer error: {e}")
        return {"status": "error", "error_message": str(e)}

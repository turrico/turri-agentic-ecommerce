from loguru import logger
from sqlalchemy.orm import selectinload

from src.turri_data_hub.embedding import compute_embeddings
from src.turri_data_hub.woocommerce.models import Product

from ...db import db
from ...utils import format_tool_args, make_numpy_values_serialiable
from .utils import _products_to_dict


async def rag_fetch_products(query: str) -> dict:
    """Fetches products from the database using a RAG (Retrieval-Augmented Generation) approach.

    Use this tool when you need a list of products most relevant to the given query.

    Args:
        query (str): The search query to find relevant products.

    Returns:
        dict: {'status': 'success', 'products': [product_dicts]} on success,
              {'status': 'error', 'error_message': str} on failure.
    """
    logger.info(format_tool_args("rag_fetch_products", query=query))

    try:
        embeddings = await compute_embeddings([query])

        products: list[Product] = await db.query_table(
            Product,
            order_by=[
                Product.embedding.l2_distance(embeddings[0]),
                Product.catalog_visibility == "visible",
                Product.status == "publish",
            ],
            limit=5,
            options=[selectinload(Product.categories), selectinload(Product.tags)],
        )

        result = {"status": "success", "products": _products_to_dict(products)}
        return make_numpy_values_serialiable(result)
    except Exception as e:
        logger.error(f"\U0001f6e0 [TOOL] rag_fetch_products error: {e}")
        return {"status": "error", "error_message": str(e)}

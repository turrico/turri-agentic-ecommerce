import numpy as np

from ..woocommerce.models import Producer, Product
from .taste_categories import TASTE_KEYS


def get_product_taste_embeddings(product: Product) -> list[bool]:
    """
    Returns a list of booleans indicating the presence of each TASTE_KEY
    in the product's tags or categories.
    """
    names = {tag.name for tag in product.tags} | {
        cat.name for cat in product.categories
    }
    return [key in names for key in TASTE_KEYS]


def get_producer_taste_embeddings(producer: Producer) -> list[float]:
    """
    Returns the average embedding for each TASTE_KEY across all products of the producer.
    Products must be loaded with their tags and categories.
    """
    product_embeddings = [product.taste_embedding for product in producer.products]
    if not product_embeddings:
        return [0.0] * len(TASTE_KEYS)
    return np.mean(product_embeddings, axis=0).tolist()

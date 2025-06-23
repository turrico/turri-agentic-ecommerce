from .categories_and_tags import (
    fetch_create_and_save_categories,
    fetch_create_and_save_tags,
)
from .customers import fetch_create_and_save_customers
from .orders import fetch_create_and_save_orders
from .producers import fetch_generate_and_save_producers
from .products import fetch_generate_and_save_products

__all__ = [
    "fetch_create_and_save_categories",
    "fetch_create_and_save_tags",
    "fetch_generate_and_save_producers",
    "fetch_generate_and_save_products",
    "fetch_create_and_save_customers",
    "fetch_create_and_save_orders",
]

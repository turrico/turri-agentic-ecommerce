from google.adk.tools import FunctionTool

from .orders import get_active_or_last_orders
from .producers import get_products_of_producer, rag_fetch_producers
from .products import rag_fetch_products
from .profile import (
    get_personalized_producer_recommendations_for_user,
    get_personalized_product_recommendations_for_user,
    get_user_profile,
    update_user_profile,
)

rag_fetch_producers_tool = FunctionTool(rag_fetch_producers)
rag_fetch_products_tool = FunctionTool(rag_fetch_products)
get_products_of_producer_tool = FunctionTool(get_products_of_producer)
get_active_or_last_orders_tool = FunctionTool(get_active_or_last_orders)
get_personalized_producer_recommendations_for_user_tool = FunctionTool(
    get_personalized_producer_recommendations_for_user
)
get_personalized_product_recommendations_for_user_tool = FunctionTool(
    get_personalized_product_recommendations_for_user
)
get_user_profile_tool = FunctionTool(get_user_profile)
update_user_profile_tool = FunctionTool(update_user_profile)

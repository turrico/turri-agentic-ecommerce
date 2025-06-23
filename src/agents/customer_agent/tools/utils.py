from src.turri_data_hub.recommendation_system.taste_categories import TASTE_KEYS
from src.turri_data_hub.woocommerce.models import Producer, Product


def _products_to_dict(products: list[Product]):
    dicts = []
    for p in products:
        p_dict = p.model_dump(
            include=[
                "id",
                "title",
                "content",
                "description",
                "producer_id",
                "price",
                "tags",
                "categories",
            ]
        )
        if p.tags:
            p_dict["tags"] = [tag.model_dump() for tag in p.tags]
        if p.categories:
            p_dict["categories"] = [tag.model_dump() for tag in p.categories]

        p_dict["taste_embedding"] = dict(zip(TASTE_KEYS, p.taste_embedding))

        dicts.append(p_dict)
    return dicts


def dump_producer(p: Producer):
    prod_dict = p.model_dump(
        exclude=[
            "link",
            "img_url",
            "products",
            "embedding",
            "taste_embedding",
        ]
    )
    prod_dict["taste_embedding"] = dict(zip(TASTE_KEYS, p.taste_embedding))
    return prod_dict

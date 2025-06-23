from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from loguru import logger
from tqdm import tqdm

from src.turri_hub.db import ProducerVectorDatabase
from src.turri_hub.models import Producer, Product, ProductCategory, ProductTag

BASE_URL = "https://turri.cr/wp-json/wp/v2/"


def fetch_list(url: str, creator, per_page: int = 50):
    items = []
    page = 1
    while True:
        full_url = f"{url}?per_page={per_page}&page={page}"
        resp = requests.get(urljoin(BASE_URL, full_url))
        if resp.status_code == 400 or not resp.json():
            break
        resp.raise_for_status()
        data = resp.json()
        for item in tqdm(data):
            try:
                items.append(creator(item))
            except Exception as e:
                logger.debug(e)

        if len(data) < per_page:
            break
        page += 1
    return items


def fetch_single(url: str, creator):
    resp = requests.get(url)
    resp.raise_for_status()
    return creator(resp.json())


def generate_producer(val: dict) -> Producer:
    img = None
    if m := val.get("_links", {}).get("wp:featuredmedia"):
        img = fetch_single(
            m[0]["href"], lambda x: x["media_details"]["sizes"]["full"]["source_url"]
        )
    if val["status"] != "publish":
        logger.info(f"unkown status '{val['status']}'")

    return Producer(
        id=val["id"],
        link=val["link"],
        title=val["title"]["rendered"],
        content=val["content"]["rendered"],
        excerpt=val["excerpt"]["rendered"],
        img_url=img,
    )


def generate_product(
    val: dict, categories: dict[int, ProductCategory], tags: dict[int, ProductTag]
) -> Product:
    img = None
    if m := val.get("_links", {}).get("wp:featuredmedia"):
        img = fetch_single(
            m[0]["href"], lambda x: x["media_details"]["sizes"]["full"]["source_url"]
        )
    if val["status"] != "publish":
        logger.info(f"unkown status '{val['status']}'")

    return Product(
        id=val["id"],
        link=val["link"],
        title=val["title"]["rendered"],
        content=val["content"]["rendered"],
        excerpt=val["excerpt"]["rendered"],
        img_url=img,
        productor_id=val["meta_box"]["producto-productor-relationship_from"][0],
        tags=[tags[i] for i in val["product_tag"] if tags[i]],
        categories=[categories[i] for i in val["product_cat"] if categories[i]],
    )


def get_text(content, excerpt):
    return BeautifulSoup(
        f"Content: {content}.\n\nExcerpt: {excerpt}", "html.parser"
    ).get_text()


def refill_vector_dbs():
    categories = {
        i.id: i
        for i in fetch_list(
            "product_cat",
            ProductCategory.model_validate,
        )
    }
    tags = {
        i.id: i
        for i in fetch_list(
            "product_tag",
            ProductTag.model_validate,
        )
    }

    producers: dict[int, Producer] = {
        i.id: i for i in fetch_list("productor", generate_producer)
    }
    products = fetch_list(
        "product", lambda x: generate_product(x, categories=categories, tags=tags)
    )

    for product in products:
        product: Product
        producers[product.productor_id].products.append(product)

    ProducerVectorDatabase.delete()

    docs = []
    ids = []
    for producer in producers.values():
        text = get_text(producer.content, producer.excerpt)
        docs.append(
            Document(
                page_content=text,
                metadata=producer.model_dump(),
            )
        )
        ids.append(producer.id)

    ids = ProducerVectorDatabase.add_documents(docs, ids=ids)
    logger.success(f"Added {len(docs)} Producers. \n Ids: {ids}")

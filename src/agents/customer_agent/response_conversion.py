from datetime import datetime

from loguru import logger
from sqlalchemy.orm import selectinload

from src.api.models import (
    FrontEndResponse,
    LineItemComponent,
    OptionQuestion,
    OrderComponent,
    PlainText,
    ProducerComponent,
    ProductComponent,
    SelectionOption,
)
from src.turri_data_hub.chatbot.models import ChatbotMention
from src.turri_data_hub.woocommerce.models import Order, Producer, Product

from ..db import db
from .internal_schema import RAGOutputNodeItem


async def convert_product(item: RAGOutputNodeItem, user_id: int) -> ProductComponent:
    product: Product = await db.query_table(
        Product,
        where_clauses=[Product.id == item.id],
        mode="first",
        options=[selectinload(Product.producer)],
    )
    if product is None:
        logger.warning(f"Agent halucinated Product {item.id}")
        return None

    mention = ChatbotMention(
        ts=datetime.now(), entity_type="product", entity_id=item.id, user_id=user_id
    )
    await db.save(mention)

    return ProductComponent(
        product_id=item.id,
        link=product.link,
        display_content=item.text,
        img_url=product.img_url,
        title=product.title,
        producer_link=product.producer.link,
        producer_name=product.producer.title,
    )


async def convert_producer(item: RAGOutputNodeItem, user_id: int) -> ProducerComponent:
    producer: Producer = await db.query_table(
        Producer, where_clauses=[Producer.id == item.id], mode="first"
    )
    if producer is None:
        logger.warning(f"Agent halucinated Producer {item.id}")
        return None

    mention = ChatbotMention(
        ts=datetime.now(), entity_type="producer", entity_id=item.id, user_id=user_id
    )
    await db.save(mention)

    return ProducerComponent(
        producer_id=item.id,
        link=producer.link,
        display_content=item.text,
        img_url=producer.img_url,
        title=producer.title,
    )


async def convert_order(item: RAGOutputNodeItem, user_id: int) -> OrderComponent:
    order: Order = await db.query_table(
        Order,
        where_clauses=[
            Order.customer_id == user_id,
            Order.id == item.id,
        ],
        options=[selectinload(Order.line_items)],
        mode="first",
    )
    if order is None:
        logger.warning(f"Agent halucinated Order {item.id}")
        return None

    items = []
    for line_item in order.line_items:
        product = await db.query_table(
            Product,
            where_clauses=[Product.id == line_item.product_id],
            mode="first",
            options=[selectinload(Product.producer)],
        )
        if product is None:
            logger.warning(f"Product of {line_item.id} lineitem not found")
            continue

        pcompontent = ProductComponent(
            product_id=product.id,
            display_content=None,
            link=product.link,
            img_url=product.img_url,
            title=product.title,
            producer_link=product.producer.link,
            producer_name=product.producer.title,
        )
        items.append(
            LineItemComponent(
                product=pcompontent, quantity=line_item.quantity, price=line_item.price
            )
        )

    return OrderComponent(
        order_id=order.id,
        display_content=item.text,
        status=order.status,
        date_created=order.date_created,
        total=order.total,
        total_tax=order.total_tax,
        line_items=items,
        currency=order.currency,
    )


async def convert_response_to_front_end_components(
    response: list[RAGOutputNodeItem],
    user_id: int,
) -> FrontEndResponse:
    result = []

    for item in response:
        if item.type == "text":
            result.append(PlainText(text=item.text))
        elif item.type == "option":
            result.append(
                OptionQuestion(
                    display_content=item.text,
                    options=[
                        SelectionOption(
                            display_content=val.text,
                            next_user_query=val.next_user_query,
                        )
                        for val in item.options
                    ],
                )
            )
        elif item.type == "product":
            res = await convert_product(item, user_id)
            if res:
                result.append(res)

        elif item.type == "producer":
            res = await convert_producer(item, user_id)
            if res:
                result.append(res)
        elif item.type == "order":
            res = await convert_order(item, user_id)
            if res:
                result.append(res)
        else:
            raise NotImplementedError(f"unknown type {item.type}")
    return result

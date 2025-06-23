from datetime import datetime
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, computed_field
from sqlmodel import Field


class TypedModel(BaseModel):
    """
    Base model for frontend components that automatically adds a 'type' field
    based on the class name.
    """

    @computed_field
    @property
    def type(self) -> str:
        return self.__class__.__name__.lower()


class PlainText(TypedModel):
    text: str = Field(description="Just plain text. No markown, No HTHML!")


class ProductComponent(TypedModel):
    product_id: int
    display_content: str | None = Field(
        description="The text you want to write about the product. Not the title, that is already handled. Just plain text. No markown, No HTHML!"
    )
    link: str
    img_url: Optional[str] = None
    producer_link: str
    producer_name: str
    title: str


class LineItemComponent(BaseModel):
    product: ProductComponent
    quantity: int
    price: float


class OrderComponent(TypedModel):
    order_id: int
    display_content: str
    date_created: datetime
    status: str
    currency: str
    total: float
    total_tax: float
    line_items: list[LineItemComponent]


class ProducerComponent(TypedModel):
    producer_id: int
    display_content: str | None = Field(
        description="The text you want to write about the producer. Not the title, that is already handled. Just plain text. No markown, No HTHML!"
    )
    link: str
    img_url: Optional[str] = None
    title: str


class SelectionOption(TypedModel):
    display_content: str
    next_user_query: str = Field(
        min_length=0,
        description=(
            "This will then send back to the chatbot, so for an "
            "option bitter could have -> 'I want to know about bitter' "
            "Very brief answer, like in a conversation."
        ),
    )


class OptionQuestion(TypedModel):
    display_content: str = Field(
        description="The question to be asked the uesr. Just plain text. No markown, No HTHML!"
    )
    options: list[SelectionOption] = Field(min_length=1, max_length=5)


FrontEndResponse = list[
    Union[OptionQuestion, PlainText, ProducerComponent, ProductComponent]
]


class ChatAnswer(BaseModel):
    """
    Response model for a chat API call.
    """

    session_uuid: UUID
    answer: FrontEndResponse | list[dict[str, Any]]
    answered_at: datetime
    stop_chat: bool = False


class ChatRequestFrontend(BaseModel):
    """
    Request model for a chat API call from the frontend.
    """

    user_id: int
    session_uuid: UUID | None
    message: str = Field(..., min_length=1)


class Conversation(BaseModel):
    """
    Model representing a full conversation history for a given session.
    """

    session_uuid: UUID
    messages: list[Union[ChatRequestFrontend, ChatAnswer]]

"""
Defines simpler representations for reliable llm generation
"""

from typing import List, Literal, Optional

from pydantic import BaseModel
from sqlmodel import Field


class SelectionOptionInternal(BaseModel):
    text: str = Field(description="The displayed text on the option Button")
    next_user_query: str = Field(
        min_length=0,
        description=(
            "This will then send back to the chatbot, so for an "
            "option bitter could have -> 'I want to know about bitter' "
            "Very brief answer, like in a conversation."
        ),
    )


class RAGOutputNodeItem(BaseModel):
    """
    Internal representation of a single component in the RAG answer.
    This schema is used for structured output from LLMs.
    """

    type: Literal["text", "producer", "product", "option", "order"] = Field(
        description="The kind of output component"
    )
    id: Optional[int] = Field(
        None,
        description="The id of the producer, product or order",
    )
    text: str = Field(description="The displayed text of the Component")
    options: Optional[List[SelectionOptionInternal]] = Field(
        None,
        description="If type==options: The options for the user else None. Not more than 3!",
    )

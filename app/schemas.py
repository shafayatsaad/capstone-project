"""API and model-output schemas. Model output is validated before persistence."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ImageTags(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(min_length=2, max_length=80)
    category: str = Field(min_length=2, max_length=40)
    attributes: list[str] = Field(min_length=1, max_length=16)
    caption: str = Field(min_length=8, max_length=500)
    confidence: float = Field(ge=0, le=1)


class PostInput(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    body: str = Field(min_length=10, max_length=8000)
    expected_category: str = Field(min_length=2, max_length=40)
    expected_subject: str = Field(min_length=2, max_length=80)


class ReviewInput(BaseModel):
    decision: Literal["approve", "reject"]
    note: str = Field(default="", max_length=1000)

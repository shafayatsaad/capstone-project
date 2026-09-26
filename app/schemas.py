from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.config import settings


class SubmissionCreate(BaseModel):
    """What a customer-site visitor's browser sends. Deliberately permissive on
    `fields` shape (widgets can define arbitrary form fields) but strict on size,
    since this input comes from the open internet and must never be trusted."""

    widget_id: str
    fields: dict[str, str] = Field(default_factory=dict)
    # Hidden honeypot field: real visitors never fill it, bots often do.
    # Name is configurable via HONEYPOT_FIELD_NAME so it isn't hardcoded/guessable
    # from the open-source repo alone.
    hp_field: str = ""
    idempotency_key: Optional[str] = Field(default=None, max_length=128)

    @field_validator("fields")
    @classmethod
    def bounded_fields(cls, v: dict[str, str]) -> dict[str, str]:
        if len(v) > settings.max_fields:
            raise ValueError(f"too many fields (max {settings.max_fields})")
        for key, value in v.items():
            if len(key) > 200:
                raise ValueError("field name too long")
            if len(value) > settings.max_field_length:
                raise ValueError(f"field '{key}' exceeds max length ({settings.max_field_length})")
        return v


class SubmissionOut(BaseModel):
    id: str
    widget_id: str
    created_at: datetime
    # Deliberately not echoing is_spam, ip_address, or geo back to the public
    # caller -- that's internal/dashboard-only information.

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    detail: str


class OwnerCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("valid email required")
        return value


class LoginRequest(OwnerCreate):
    password: str = Field(min_length=1, max_length=128)


class WidgetField(BaseModel):
    name: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,63}$")
    label: str = Field(min_length=1, max_length=100)
    type: str = Field(default="text", pattern=r"^(text|email|tel|textarea)$")
    required: bool = True


class WidgetCreate(BaseModel):
    type: str = Field(default="signup_form", pattern=r"^(signup_form|cta|popover)$")
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    fields: list[WidgetField] = Field(default_factory=list, max_length=20)
    button_text: str = Field(default="Submit", min_length=1, max_length=40)
    display_options: dict = Field(default_factory=dict)

    @field_validator("fields")
    @classmethod
    def unique_names(cls, fields):
        names = [item.name for item in fields]
        if len(names) != len(set(names)):
            raise ValueError("field names must be unique")
        return fields


class WidgetUpdate(WidgetCreate):
    pass


class WidgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    type: str
    title: str
    description: str
    fields: list[dict]
    button_text: str
    display_options: dict
    version: int

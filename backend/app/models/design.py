from __future__ import annotations

from typing import Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class Design(SQLModel, table=True):
    __tablename__ = "designs"

    id: str = Field(default=None, primary_key=True)
    name: str
    tradition: str = "kolam"
    category: str = "pattern"
    description: str = ""
    original_image_path: str | None = None
    created_at: str
    updated_at: str
    design_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    grammar: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    analysis: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    parameters: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

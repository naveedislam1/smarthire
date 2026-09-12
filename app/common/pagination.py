"""Reusable pagination primitives for list endpoints."""

from typing import Annotated

from fastapi import Query
from pydantic import BaseModel


class PaginationParams(BaseModel):
    """Query parameters controlling offset-based pagination."""

    limit: Annotated[int, Query(ge=1, le=100)] = 20
    offset: Annotated[int, Query(ge=0)] = 0


class Page[T](BaseModel):
    """A single page of results plus the total count for the query."""

    items: list[T]
    total: int
    limit: int
    offset: int

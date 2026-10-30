"""Allowlisted tools the model may plan. Each module owns its args contract (and, from M5, its run())."""

from typing import Annotated, Union

from pydantic import Field

from tools.add_item import AddItemArgs, AddItemCall
from tools.search_items import DateRange, SearchItemsArgs, SearchItemsCall
from tools.update_item import UpdateItemArgs, UpdateItemCall

# The union is the allowlist: any other `name` fails validation.
ToolCall = Annotated[
    Union[AddItemCall, UpdateItemCall, SearchItemsCall],
    Field(discriminator="name"),
]

__all__ = [
    "AddItemArgs",
    "AddItemCall",
    "DateRange",
    "SearchItemsArgs",
    "SearchItemsCall",
    "ToolCall",
    "UpdateItemArgs",
    "UpdateItemCall",
]

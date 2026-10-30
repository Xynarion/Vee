"""Tool args contracts (no DB)."""

from datetime import date

import pytest
from pydantic import TypeAdapter, ValidationError

from tools import AddItemArgs, SearchItemsArgs, ToolCall, UpdateItemArgs

ITEM_ID = "itm_a1b2c3d4e5f67890"
call_adapter = TypeAdapter(ToolCall)


# --- ToolCall union ---


def test_tool_call_picks_args_model_by_name() -> None:
    call = call_adapter.validate_python({"name": "search_items", "args": {"query": "acme"}})
    assert isinstance(call.args, SearchItemsArgs)


def test_unknown_tool_rejected() -> None:
    with pytest.raises(ValidationError):
        call_adapter.validate_python({"name": "delete_item", "args": {"id": ITEM_ID}})


# --- add_item ---


def test_add_item_omitted_fields_default() -> None:
    args = AddItemArgs(title="Call the doctor", type="task")
    assert args.status == "todo"
    assert args.due_at is None and args.work_mode is None and args.parent_id is None


def test_add_item_unknown_arg_rejected() -> None:
    with pytest.raises(ValidationError):
        AddItemArgs(title="Call the doctor", type="task", priority="high")


def test_add_item_naive_datetime_rejected() -> None:
    with pytest.raises(ValidationError):
        AddItemArgs(title="Call the doctor", type="task", due_at="2026-10-22T09:00:00")


def test_add_item_bad_enum_rejected() -> None:
    with pytest.raises(ValidationError):
        AddItemArgs(title="Call the doctor", type="reminder")


# --- update_item ---


def test_update_item_changes_exclude_omitted_fields() -> None:
    args = UpdateItemArgs(id=ITEM_ID, due_at="2026-10-22T00:00:00+01:00")
    assert set(args.changes()) == {"due_at"}


def test_update_item_null_clears() -> None:
    args = UpdateItemArgs(id=ITEM_ID, due_at=None)
    assert args.changes() == {"due_at": None}


def test_update_item_title_is_a_rename() -> None:
    args = UpdateItemArgs(id=ITEM_ID, title="Chase the Acme invoice")
    assert args.changes() == {"title": "Chase the Acme invoice"}


def test_update_item_without_changes_rejected() -> None:
    with pytest.raises(ValidationError):
        UpdateItemArgs(id=ITEM_ID)


def test_update_item_new_title_rejected() -> None:
    with pytest.raises(ValidationError):
        UpdateItemArgs(id=ITEM_ID, new_title="Chase the Acme invoice", status="completed")


def test_update_item_cannot_clear_title_status_or_type() -> None:
    with pytest.raises(ValidationError):
        UpdateItemArgs(id=ITEM_ID, title=None, status="completed")
    with pytest.raises(ValidationError):
        UpdateItemArgs(id=ITEM_ID, status=None)
    with pytest.raises(ValidationError):
        UpdateItemArgs(id=ITEM_ID, type=None)


def test_update_item_bad_id_rejected() -> None:
    with pytest.raises(ValidationError):
        UpdateItemArgs(id="Chase Acme", status="completed")


# --- search_items ---


def test_search_items_no_filters_allowed() -> None:
    assert SearchItemsArgs().model_dump(exclude_none=True) == {}


def test_search_items_single_value_coerced_to_list() -> None:
    args = SearchItemsArgs(status="blocked", type="task", work_mode="building")
    assert args.status == ["blocked"] and args.type == ["task"] and args.work_mode == ["building"]


def test_search_items_combined_filters() -> None:
    args = SearchItemsArgs(
        status=["completed", "dropped"],
        updated={"after": "2026-10-14", "before": "2026-10-21T23:59:59+01:00"},
        carried=True,
        sort_by="updated_at",
        sort_order="desc",
        limit=20,
    )
    assert args.updated.after == date(2026, 10, 14)
    assert args.updated.before.utcoffset().total_seconds() == 3600


def test_search_items_bad_status_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchItemsArgs(status=["done"])


def test_search_items_naive_bound_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchItemsArgs(due={"before": "2026-10-22T09:00:00"})


def test_search_items_empty_range_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchItemsArgs(due={})


def test_search_items_contradiction_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchItemsArgs(has_due_at=False, due={"before": "2026-10-22"})


def test_search_items_sort_order_needs_sort_by() -> None:
    with pytest.raises(ValidationError):
        SearchItemsArgs(sort_order="asc")


def test_search_items_limit_bounds() -> None:
    with pytest.raises(ValidationError):
        SearchItemsArgs(limit=0)
    with pytest.raises(ValidationError):
        SearchItemsArgs(limit=500)


def test_search_items_bad_id_rejected() -> None:
    with pytest.raises(ValidationError):
        SearchItemsArgs(ids=["Chase Acme"])

"""format_reply turns testimony item ids into a header and alignment symbols."""

from __future__ import annotations

from types import SimpleNamespace

from lab.fixtures.remembering import golden_decision_01
from llm.schema import Decision

TASK = "itm_" + "ab" * 8
EVENT = "itm_" + "cd" * 8
MISSING = "itm_" + "ef" * 8


def build_testimony(item_ids: list[str], *, text: str = "What you have today") -> Decision:
    payload = golden_decision_01()
    payload["say"]["text"] = text
    payload["say"]["testimony"]["item_ids"] = item_ids
    payload["say"]["testimony"]["omitted_ids"] = []
    payload["say"]["testimony"]["omitted_ids_reason"] = None
    return Decision.model_validate(payload)


def confirmation_decision() -> Decision:
    payload = golden_decision_01()
    payload["say"] = {"types": ["confirmation"], "text": "Recorded.", "testimony": None}
    return Decision.model_validate(payload)


def items() -> list[SimpleNamespace]:
    return [
        SimpleNamespace(id=TASK, type="task", title="Finalize landing copy"),
        SimpleNamespace(id=EVENT, type="event", title="Family meeting"),
    ]


def show_reply(heading: str, reply: str | None) -> None:
    print(f"\n\033[1m{heading}\033[0m")
    print("─" * len(heading))
    if reply is None:
        print("  (no reply)")
        return
    for line in reply.splitlines():
        print(f"  {line}")


def test_format_reply_lists_symbols_in_testimony_order() -> None:
    from api.telegram.reply import format_reply

    reply = format_reply(build_testimony([EVENT, TASK, MISSING]), items())
    show_reply("testimony list, event then task; missing id dropped", reply)
    assert reply == "What you have today\n○ Family meeting\n• Finalize landing copy"


def test_format_reply_skips_a_missing_id() -> None:
    from api.telegram.reply import format_reply

    reply = format_reply(build_testimony([MISSING, TASK]), items())
    show_reply("missing id first, then the task", reply)
    assert reply == "What you have today\n• Finalize landing copy"


def test_format_reply_without_testimony_returns_none() -> None:
    from api.telegram.reply import format_reply

    reply = format_reply(confirmation_decision(), items())
    show_reply("confirmation, no testimony", reply)
    assert reply is None


def test_format_reply_with_no_visible_lines_returns_none() -> None:
    from api.telegram.reply import format_reply

    reply = format_reply(build_testimony([MISSING], text="  "), [])
    show_reply("blank header and an id that is not loaded", reply)
    assert reply is None

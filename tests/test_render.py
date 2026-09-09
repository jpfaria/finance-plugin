import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from finance.render.output import to_jsonable


@dataclass(frozen=True)
class _Inner:
    when: date
    value: Decimal


@dataclass(frozen=True)
class _Outer:
    name: str
    items: list[_Inner]
    maybe: Decimal | None
    pct: str | None


def test_to_jsonable() -> None:
    obj = _Outer("x", [_Inner(date(2026, 9, 1), Decimal("1.5"))], None, "13.3")
    data = to_jsonable(obj)
    assert data == {
        "name": "x",
        "items": [{"when": "2026-09-01", "value": "1.50"}],
        "maybe": None,
        "pct": "13.3",
    }
    json.dumps(data)

"""Contract every statement parser implements."""

from pathlib import Path
from typing import Protocol

from finance.imports.record import ImportedRecord


class Parser(Protocol):
    name: str

    def matches(self, path: Path, head: str) -> bool: ...

    def parse(self, path: Path) -> list[ImportedRecord]: ...

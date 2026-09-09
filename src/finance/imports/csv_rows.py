"""Read a CSV statement as dict rows (shared by the CSV parsers)."""

import csv
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def header_line(head: str) -> str:
    return head.lstrip("﻿").splitlines()[0].strip() if head.strip() else ""

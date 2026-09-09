"""Pick the parser for a statement file by extension / header signature."""

from pathlib import Path

from finance.imports.nubank_card_csv import NubankCardCsv
from finance.imports.nubank_checking_csv import NubankCheckingCsv
from finance.imports.ofx import OfxParser
from finance.imports.parser import Parser
from finance.model.errors import FinanceError

PARSERS: tuple[Parser, ...] = (OfxParser(), NubankCheckingCsv(), NubankCardCsv())
HEAD_CHARS = 512


def detect(path: Path) -> Parser:
    head = path.read_text(encoding="utf-8", errors="replace")[:HEAD_CHARS]
    for parser in PARSERS:
        if parser.matches(path, head):
            return parser
    names = ", ".join(p.name for p in PARSERS)
    raise FinanceError(
        f"formato não reconhecido: {path.name}. Formatos suportados: {names}. "
        "Para outro banco/formato, abra uma issue com um extrato anonimizado."
    )

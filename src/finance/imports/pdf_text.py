"""Camada de texto de um PDF — único lugar do projeto que conhece o pypdf."""

from pathlib import Path
from typing import Final

from pypdf import PdfReader

PAGE_SEPARATOR = "\n"
LAYOUT_MODE: Final = "layout"


def extract_text(path: Path) -> str:
    """Texto de todas as páginas, na ordem, separadas por linha.

    PDF sem camada de texto (imagem escaneada) devolve string vazia; quem
    chama decide o que fazer — aqui nada é inventado.
    """
    with path.open("rb") as fh:
        reader = PdfReader(fh)
        return PAGE_SEPARATOR.join(page.extract_text() or "" for page in reader.pages)


def extract_layout_pages(path: Path) -> list[str]:
    """Texto de cada página preservando as colunas, uma string por página.

    O modo layout do pypdf reconstrói a posição horizontal com espaços: é o
    único jeito de saber em qual coluna um número está (crédito ou débito) num
    extrato que não repete o rótulo em cada linha. O texto é devolvido por
    página porque os offsets das colunas variam de uma pra outra.
    """
    with path.open("rb") as fh:
        reader = PdfReader(fh)
        return [page.extract_text(extraction_mode=LAYOUT_MODE) or "" for page in reader.pages]

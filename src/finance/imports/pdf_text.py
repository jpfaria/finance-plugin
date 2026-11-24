"""Camada de texto de um PDF — único lugar do projeto que conhece o pypdf."""

from pathlib import Path

from pypdf import PdfReader

PAGE_SEPARATOR = "\n"


def extract_text(path: Path) -> str:
    """Texto de todas as páginas, na ordem, separadas por linha.

    PDF sem camada de texto (imagem escaneada) devolve string vazia; quem
    chama decide o que fazer — aqui nada é inventado.
    """
    with path.open("rb") as fh:
        reader = PdfReader(fh)
        return PAGE_SEPARATOR.join(page.extract_text() or "" for page in reader.pages)

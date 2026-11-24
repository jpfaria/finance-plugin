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


def extract_layout_pages(path: Path) -> list[str]:
    """Texto de cada página preservando a posição horizontal de cada coluna.

    Quem lê tabela de extrato precisa saber em QUE coluna o valor está (crédito
    ou débito); no texto plano essa informação não existe.
    """
    with path.open("rb") as fh:
        reader = PdfReader(fh)
        return [page.extract_text(extraction_mode="layout") or "" for page in reader.pages]

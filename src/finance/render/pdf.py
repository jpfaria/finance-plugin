"""Turn an HTML page into a PDF with the browser already installed on the machine.

Nenhuma dependência nova: quem imprime é o Chrome/Chromium em modo headless. O
HTML fica salvo ao lado do PDF, pra dar pra abrir e reimprimir sem rodar nada.
`FINANCE_BROWSER` força um executável.
"""

import os
import subprocess
from pathlib import Path

from finance.model.errors import FinanceError

BROWSER_ENV = "FINANCE_BROWSER"
TIMEOUT_SECONDS = 120
CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
)


def find_browser() -> Path:
    forced = os.environ.get(BROWSER_ENV, "").strip()
    if forced:
        path = Path(forced)
        if not path.exists():
            raise FinanceError(f"{BROWSER_ENV} aponta pra algo que não existe: {path}")
        return path
    for candidate in CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return path
    raise FinanceError(
        "não achei Chrome, Chromium ou Edge pra imprimir o PDF. "
        f"Instale um deles ou aponte {BROWSER_ENV} pro executável."
    )


def html_to_pdf(html: Path, pdf: Path) -> None:
    """Imprime `html` em `pdf`. Erro claro se o navegador não gerar o arquivo."""
    browser = find_browser()
    pdf.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf}",
        html.resolve().as_uri(),
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise FinanceError(f"o navegador travou imprimindo {html.name}") from exc
    if not pdf.exists():
        detail = (result.stderr or result.stdout or "").strip().splitlines()
        tail = detail[-1] if detail else f"código {result.returncode}"
        raise FinanceError(f"o navegador não gerou {pdf.name}: {tail}")

"""Gera `tests/fixtures/bradesco_checking.pdf` — dado fictício, geometria real.

    uv run python tools/make_bradesco_checking_fixture.py tests/fixtures/bradesco_checking.pdf

Nome, agência, conta, favorecidos, valores e doctos são inventados; nada aqui é
dado de ninguém. O que foi copiado do extrato real (medido com um visitor do
pypdf) é só a geometria, e ela é o que importa: o x de cada coluna, o histórico
4,5pt acima da linha de valores, o detalhe 4,5pt abaixo, um BT/ET por fragmento
e o passo de 30,4pt entre linhas. É essa geometria que faz o pypdf em
`extraction_mode="layout"` montar as linhas como no PDF do banco — com outra, a
fixture passa a testar um layout que não existe.
"""

import zlib
from pathlib import Path

FONT_SIZE = 7.99
TITLE_SIZE = 12.75
DIGIT = 0.500 * FONT_SIZE
PUNCT = 0.250 * FONT_SIZE

X_HEADER_BLOCK = 200.2
X_LEFT = 46.0
X_HISTORY = 109.5
X_DOCTO = 303.0
X_SALDO = 522.5
X_FOLHA = 518.3
CREDIT_RIGHT = 426.8
DEBIT_RIGHT = 490.5
HISTORY_LIFT = 4.5
ROW_STEP = 30.4
FIRST_ROW_Y = 644.7

PAGE_HEADER = [
    (X_HEADER_BLOCK, 777.0, "Bradesco Celular", "F2", TITLE_SIZE),
    (X_HEADER_BLOCK, 755.3, "Data: 10/03/2026 - 09h15", "F1", FONT_SIZE),
    (X_HEADER_BLOCK, 742.6, "Nome: MARIA EXEMPLO DOS SANTOS", "F1", FONT_SIZE),
    (X_LEFT, 713.0, "Extrato de: Agência: 123 | Conta: 4567-8", "F1", FONT_SIZE),
    (X_LEFT + 0.1, 680.7, "Data", "F1", FONT_SIZE),
    (110.6, 680.7, "Histórico", "F1", FONT_SIZE),
    (304.9, 680.7, "Docto.", "F1", FONT_SIZE),
    (385.0, 680.7, "Crédito (R$)", "F1", FONT_SIZE),
    (451.7, 680.7, "Débito (R$)", "F1", FONT_SIZE),
    (519.8, 680.7, "Saldo (R$)", "F1", FONT_SIZE),
]

# (data, histórico, docto, crédito, débito, saldo, detalhe)
PAGE_1_ROWS = [
    (
        "02/03/2026",
        "PIX RECEBIDO",
        "1000001",
        "1.234,56",
        "",
        "5.000,00",
        "REM: EMPRESA EXEMPLO S.A. 02/03",
    ),
    ("", "PIX ENVIADO", "1000002", "", "200,00", "4.800,00", "DES: Fulano de Exemplo 01/03"),
    ("", "CONTA DE LUZ", "1000003", "", "158,00", "4.642,00", "LUZ EXEMPLO-RJ-9999999999"),
    ("", "IOF S/ UTILIZACAO LIMITE", "0000569", "", "23,95", "4.618,05", ""),
    (
        "05/03/2026",
        "ENCARGOS LIMITE DE CRED",
        "0000569",
        "",
        "77,25",
        "4.540,80",
        "ENCARGO - 07,73%",
    ),
]
PAGE_2_ROWS = [
    (
        "06/03/2026",
        "PIX QR CODE ESTATICO",
        "1000006",
        "",
        "1.920,00",
        "2.620,80",
        "DES: LOJA EXEMPLO LTDA 06/03",
    ),
    (
        "",
        "TRANSF SALDO C/SAL P/CC",
        "1000007",
        "3.000,00",
        "",
        "5.620,80",
        "EMPREGADOR EXEMPLO LTDA",
    ),
    ("07/03/2026", "GASTOS CARTAO DE CREDITO", "1000008", "", "1.000,00", "4.620,80", ""),
]
TOTAL_ROW = ("4.234,56", "3.379,20", "4.620,80")


def width(text: str) -> float:
    return sum(DIGIT if c.isdigit() else PUNCT for c in text)


def fragments(rows: list[tuple[str, ...]], folha: str, total: bool) -> list[tuple]:
    out = [(x, y, t, f, s) for x, y, t, f, s in PAGE_HEADER]
    out.append((X_FOLHA, 711.1, f"Folha: {folha}", "F1", 10.01))
    y = FIRST_ROW_Y
    for day, history, docto, credit, debit, saldo, detail in rows:
        # Mesma ordem e mesmos y do extrato real: data, histórico 4,5pt acima,
        # detalhe 4,5pt abaixo, depois docto, valor e saldo.
        if day:
            out.append((X_LEFT - 0.2, y, day, "F1", FONT_SIZE))
        out.append((X_HISTORY, y + HISTORY_LIFT, history + " ", "F1", FONT_SIZE))
        if detail:
            out.append((X_HISTORY, y - HISTORY_LIFT, detail, "F1", FONT_SIZE))
        out.append((X_DOCTO, y, docto, "F1", FONT_SIZE))
        if credit:
            out.append((CREDIT_RIGHT - width(credit), y, credit, "F1", FONT_SIZE))
        if debit:
            out.append((DEBIT_RIGHT - width(debit), y, debit, "F1", FONT_SIZE))
        out.append((X_SALDO, y, saldo, "F1", FONT_SIZE))
        y -= ROW_STEP
    if total:
        credit, debit, saldo = TOTAL_ROW
        out.append((X_LEFT, y, "Total", "F1", FONT_SIZE))
        out.append((CREDIT_RIGHT - width(credit), y, credit, "F1", FONT_SIZE))
        out.append((DEBIT_RIGHT - width(debit), y, debit, "F1", FONT_SIZE))
        out.append((X_SALDO, y, saldo, "F1", FONT_SIZE))
    return out


def escape(text: str) -> bytes:
    raw = text.encode("cp1252")
    for char, replacement in ((b"\\", b"\\\\"), (b"(", b"\\("), (b")", b"\\)")):
        raw = raw.replace(char, replacement)
    return raw


def content(frags: list[tuple]) -> bytes:
    # Um BT/ET por fragmento, como o PDF do banco: é o que faz o pypdf em
    # extraction_mode="layout" juntar o histórico (4,5pt acima) na linha dos
    # valores e deixar o detalhe (4,5pt abaixo) em linha separada.
    parts = []
    for x, y, text, font, size in frags:
        parts.append(f"BT\n/{font} {size} Tf\n1 0 0 1 {x:.2f} {y:.2f} Tm\n".encode())
        parts.append(b"(" + escape(text) + b")Tj\nET\n")
    return b"".join(parts)


def build(path: Path) -> None:
    streams = [
        content(fragments(PAGE_1_ROWS, "1/2", total=False)),
        content(fragments(PAGE_2_ROWS, "2/2", total=True)),
    ]
    objects: dict[int, bytes] = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = b" ".join(f"{5 + 2 * i} 0 R".encode() for i in range(len(streams)))
    objects[2] = b"<< /Type /Pages /Count %d /Kids [%s] >>" % (len(streams), kids)
    objects[3] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >>"
    )
    objects[4] = (
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold /Encoding /WinAnsiEncoding >>"
    )
    for index, stream in enumerate(streams):
        page_id = 5 + 2 * index
        objects[page_id] = (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.88] "
            b"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents %d 0 R >>" % (page_id + 1)
        )
        packed = zlib.compress(stream)
        objects[page_id + 1] = (
            b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(packed)
            + packed
            + b"\nendstream"
        )
    out = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += b"%d 0 obj\n" % number + objects[number] + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for number in sorted(objects):
        out += b"%010d 00000 n \n" % offsets[number]
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref_at,
    )
    path.write_bytes(bytes(out))


if __name__ == "__main__":
    import sys

    build(Path(sys.argv[1]))

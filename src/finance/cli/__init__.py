"""Typer app: only wiring, no business rules."""

from typing import Annotated

import typer

from finance import __version__
from finance.cli.add import add
from finance.cli.rebuild import rebuild

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_version_callback, is_eager=True, help="Mostra a versão."
        ),
    ] = False,
) -> None:
    """finance — controle financeiro pessoal."""


app.command("add")(add)
app.command("rebuild")(rebuild)

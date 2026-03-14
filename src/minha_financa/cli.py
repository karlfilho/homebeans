"""Interface CLI com Typer e Rich."""

from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from minha_financa.models import Posting, Transaction
from minha_financa.reports import balance_report
from minha_financa.storage import load_ledger, save_ledger

load_dotenv()

app = typer.Typer(
    name="minha-financa",
    help="Sistema de Contabilidade de Partida Dobrada inspirado no hledger.",
)
console = Console()


def _get_ledger_path() -> Path:
    import os
    path = os.getenv("LEDGER_PATH", "./data/ledger.yaml")
    return Path(path)


@app.command()
def add(
    date_str: str = typer.Option(..., "--date", "-D", help="Data (YYYY-MM-DD)"),
    description: str = typer.Option(..., "--desc", "-d", help="Descrição da transação"),
    postings: list[str] = typer.Argument(
        ...,
        help='Postings no formato "conta:valor", ex: assets:bank:100 expenses:food:-100',
    ),
) -> None:
    """Adiciona uma transação ao livro-razão."""
    from datetime import datetime
    from decimal import Decimal

    ledger_path = _get_ledger_path()
    transactions = load_ledger(ledger_path)

    postings_list: list[Posting] = []
    for s in postings:
        parts = s.rsplit(":", 1)
        if len(parts) != 2:
            console.print(f"[red]Posting inválido: {s}[/red]")
            raise typer.Exit(1)
        account, amount_str = parts[0], parts[1]
        try:
            amount = Decimal(amount_str.strip())
        except Exception:
            console.print(f"[red]Valor inválido: {amount_str}[/red]")
            raise typer.Exit(1)
        postings_list.append(Posting(account=account.strip(), amount=amount))

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        console.print(f"[red]Data inválida: {date_str} (use YYYY-MM-DD)[/red]")
        raise typer.Exit(1)

    try:
        t = Transaction(date=dt, description=description, postings=postings_list)
    except Exception as e:
        console.print(f"[red]Erro de validação: {e}[/red]")
        raise typer.Exit(1)

    transactions.append(t)
    save_ledger(ledger_path, transactions)
    console.print("[green]Transação adicionada com sucesso.[/green]")


@app.command()
def balance() -> None:
    """Exibe o balanço por conta."""
    ledger_path = _get_ledger_path()
    transactions = load_ledger(ledger_path)
    report = balance_report(transactions)

    table = Table(title="Balanço por Conta")
    table.add_column("Conta", style="cyan")
    table.add_column("Saldo", justify="right", style="green")
    for account, bal in report:
        table.add_row(account, str(bal))
    console.print(table)


@app.command()
def report(
    limit: int = typer.Option(20, "--limit", "-n", help="Número de transações"),
) -> None:
    """Lista as últimas transações."""
    ledger_path = _get_ledger_path()
    transactions = load_ledger(ledger_path)
    recent = transactions[-limit:]

    table = Table(title=f"Últimas {limit} transações")
    table.add_column("Data", style="dim")
    table.add_column("Descrição", style="cyan")
    table.add_column("Lançamentos", style="green")
    for t in reversed(recent):
        postings_str = "; ".join(
            f"{p.account} {p.amount}" for p in t.postings
        )
        table.add_row(str(t.date), t.description, postings_str)
    console.print(table)


@app.command()
def chart(
    output: Path = typer.Option(
        Path("balance_chart.html"),
        "--output",
        "-o",
        help="Arquivo HTML de saída",
    ),
) -> None:
    """Gera gráfico de saldo por conta (HTML)."""
    from decimal import Decimal

    from minha_financa.viz import export_balance_chart

    ledger_path = _get_ledger_path()
    transactions = load_ledger(ledger_path)
    report = balance_report(transactions)
    balances = {acc: float(bal) for acc, bal in report}
    export_balance_chart(balances, output)
    console.print(f"[green]Gráfico exportado para {output}[/green]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()

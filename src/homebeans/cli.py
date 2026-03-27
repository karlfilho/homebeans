"""Interface CLI com Typer e Rich."""

from pathlib import Path

import questionary
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.tree import Tree

from homebeans.config import get_ledger_path
from homebeans.models import Posting, Transaction
from homebeans.reports import balance_report
from homebeans.storage import load_ledger, save_ledger
from homebeans.suggester import extract_all_accounts, suggest_for_description

load_dotenv()

app = typer.Typer(
    name="homebeans",
    help="Sistema de Contabilidade de Partida Dobrada inspirado no hledger.",
)
console = Console()

ACCOUNT_ROOTS = {
    "ativos": "ativos",
    "passivos": "passivos",
    "despesas": "despesas",
    "entradas": "entradas",
    "patrimônio": "patrimônio",
    "patrimonio": "patrimônio",
}


def _account_type(account: str) -> str:
    root = account.split(":", 1)[0].strip().lower()
    return ACCOUNT_ROOTS.get(root, "outras")


def _build_account_tree(accounts: list[str]) -> Tree:
    root = Tree("Contas", guide_style="dim")
    nodes: dict[tuple[str, ...], Tree] = {(): root}
    for acc in accounts:
        parts = [p for p in acc.split(":") if p]
        path: tuple[str, ...] = ()
        for part in parts:
            parent = nodes[path]
            path = (*path, part)
            if path not in nodes:
                nodes[path] = parent.add(part)
    return root


@app.command("journal-clear")
def journal_clear() -> None:
    """Limpa o journal (remove todas as transações) com confirmação."""
    ledger_path = get_ledger_path()
    console.print(
        Panel(
            "[bold red]ATENÇÃO[/bold red]\n"
            "Isso vai remover TODAS as transações do journal.",
            border_style="red",
            title="Limpar journal",
        )
    )
    if not Confirm.ask("Tem certeza que deseja continuar?", default=False):
        console.print("[yellow]Operação cancelada.[/yellow]")
        raise typer.Exit(0)

    try:
        _ = load_ledger(ledger_path)
    except Exception as e:
        console.print("[red]Erro ao carregar o journal atual.[/red]")
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    save_ledger(ledger_path, [])
    console.print("[green]Journal limpo com sucesso.[/green]")


@app.command()
def accounts(
    tree: bool = typer.Option(False, "--tree", help="Exibe hierarquia de contas"),
    a: bool = typer.Option(False, "--a", help="Somente ativos"),
    p: bool = typer.Option(False, "--p", help="Somente passivos"),
    d: bool = typer.Option(False, "--d", help="Somente despesas"),
    r: bool = typer.Option(False, "--r", help="Somente entradas"),
    e: bool = typer.Option(False, "--e", help="Somente patrimônio"),
    o: bool = typer.Option(False, "--o", help="Somente outras"),
) -> None:
    """Lista contas em uso no journal, com filtros por tipo e opção em árvore."""
    ledger_path = get_ledger_path()
    transactions = load_ledger(ledger_path)
    all_accounts = extract_all_accounts(transactions)

    by_type: dict[str, list[str]] = {
        "ativos": [],
        "passivos": [],
        "despesas": [],
        "entradas": [],
        "patrimônio": [],
        "outras": [],
    }
    for acc in all_accounts:
        by_type[_account_type(acc)].append(acc)

    selected_types: list[str] = []
    if a:
        selected_types.append("ativos")
    if p:
        selected_types.append("passivos")
    if d:
        selected_types.append("despesas")
    if r:
        selected_types.append("entradas")
    if e:
        selected_types.append("patrimônio")
    if o:
        selected_types.append("outras")
    if not selected_types:
        selected_types = ["ativos", "passivos", "despesas", "entradas", "patrimônio", "outras"]

    if tree:
        for t in selected_types:
            accounts_list = by_type[t]
            if not accounts_list:
                continue
            console.print(
                Panel(
                    _build_account_tree(accounts_list),
                    title=t.capitalize(),
                    title_align="left",
                )
            )
        return

    for t in selected_types:
        accounts_list = by_type[t]
        if not accounts_list:
            continue
        table = Table(
            title=t.capitalize(),
            title_justify="left",
            show_header=False,
            border_style="blue",
        )
        table.add_column("Conta", style="cyan")
        for acc in accounts_list:
            table.add_row(acc)
        console.print(table)


def _ask_date(today_str: str) -> str | None:
    """Pergunta a data ao usuário. Retorna string válida ou None para sair."""
    from datetime import datetime
    while True:
        date_str = questionary.text("Data (YYYY-MM-DD):", default=today_str).ask()
        if date_str is None or date_str.strip() == "<":
            return None
        date_str = date_str.strip()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return date_str
        except ValueError:
            console.print(f"[red]Data inválida: {date_str} (use YYYY-MM-DD)[/red]")


@app.command()
def add() -> None:
    """Adiciona uma transação ao livro-razão via wizard interativo."""
    from datetime import date, datetime
    from decimal import Decimal, InvalidOperation

    ledger_path = get_ledger_path()
    console.print("[green]Tudo certo, vamos começar.[/green]")
    console.print(
        "[dim]Dica: use '<' para voltar ao passo anterior ou cancelar quando indicado.[/dim]"
    )
    console.print(
        "[dim]Dica: tags seguem o formato chave:valor (ex: veiculo:meteor, viagem:sp).[/dim]"
    )

    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        console.print("[red]Erro ao carregar o journal de transações.[/red]")
        console.print(f"[red]{e}[/red]")
        console.print(
            "[yellow]Corrija o arquivo de journal antes de adicionar novas transações.[/yellow]"
        )
        raise typer.Exit(1)

    if not ledger_path.exists():
        console.print(
            "[yellow]Journal ainda não existe. Ele será criado ao salvar a primeira transação.[/yellow]"
        )

    all_accounts = extract_all_accounts(transactions)

    while True:
        today_str = date.today().isoformat()
        postings_list: list[Posting] = []
        saldo = Decimal("0")
        is_first_posting = True

        # --- Data ---
        date_str = _ask_date(today_str)
        if date_str is None:
            if Confirm.ask("Deseja sair sem salvar?", default=True):
                console.print("[yellow]Operação cancelada.[/yellow]")
                raise typer.Exit(0)
            continue
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()

        # --- Descrição ---
        description: str | None = None
        while description is None:
            desc_input = questionary.text("Descrição da transação:").ask()
            if desc_input is None or desc_input.strip() == "<":
                date_str = _ask_date(today_str)
                if date_str is None:
                    if Confirm.ask("Deseja sair sem salvar?", default=True):
                        console.print("[yellow]Operação cancelada.[/yellow]")
                        raise typer.Exit(0)
                else:
                    dt = datetime.strptime(date_str, "%Y-%m-%d").date()
                continue
            desc_input = desc_input.strip()
            if not desc_input:
                console.print("[red]Descrição não pode ser vazia.[/red]")
                continue
            description = desc_input

        # --- Tags da transação ---
        transaction_tags: list[str] = []
        while True:
            tags_input = questionary.text(
                "Tags da transação (opcional, separadas por espaço ou vírgula, formato chave:valor):",
            ).ask()
            if tags_input is None:
                if Confirm.ask("Deseja sair sem salvar?", default=True):
                    console.print("[yellow]Operação cancelada.[/yellow]")
                    raise typer.Exit(0)
                continue
            tags_raw = tags_input.strip()
            if tags_raw == "<":
                description = None
                break
            if tags_raw:
                import re
                parts = re.split(r"[,\s]+", tags_raw)
                transaction_tags = [p.strip() for p in parts if p.strip()]
            break

        if description is None:
            continue

        # Sugestões com base na descrição.
        suggested_posting, suggested_amount = suggest_for_description(transactions, description)

        # --- Loop de lançamentos ---
        while True:
            console.print(f"[blue]Saldo atual da transação: {saldo}[/blue]")
            if saldo != 0:
                console.print(f"[yellow]Falta {(-saldo)} para zerar.[/yellow]")

            default_account = ""
            if is_first_posting and suggested_posting is not None:
                default_account = suggested_posting.account

            posting_index = len(postings_list) + 1
            account = questionary.autocomplete(
                f"Conta ({posting_index}):",
                choices=all_accounts,
                default=default_account,
            ).ask()
            if account is None:
                if Confirm.ask("Cancelar esta transação?", default=True):
                    console.print("[yellow]Transação cancelada pelo usuário.[/yellow]")
                    raise typer.Exit(0)
                continue
            account = account.strip()
            if account == "<":
                description = None
                break

            default_amount_str = ""
            if is_first_posting and suggested_amount is not None:
                default_amount_str = str(suggested_amount)
            elif saldo != 0:
                default_amount_str = str(-saldo)

            amount_str = questionary.text("Valor:", default=default_amount_str).ask()
            if amount_str is None:
                if Confirm.ask("Cancelar esta transação?", default=True):
                    console.print("[yellow]Transação cancelada pelo usuário.[/yellow]")
                    raise typer.Exit(0)
                continue
            amount_str = amount_str.strip()
            if amount_str == "<":
                continue

            try:
                amount = Decimal(amount_str)
            except (InvalidOperation, ValueError):
                console.print(f"[red]Valor inválido: {amount_str}[/red]")
                continue

            try:
                posting = Posting(account=account, amount=amount, tags=transaction_tags)
            except Exception as e:
                console.print(f"[red]Erro de validação no lançamento: {e}[/red]")
                continue

            postings_list.append(posting)
            saldo += posting.amount
            is_first_posting = False

            if saldo == 0:
                console.print("[green]Saldo da transação zerado.[/green]")
                break

        if description is None:
            continue

        try:
            t = Transaction(date=dt, description=description, postings=postings_list)
        except Exception as e:
            console.print(f"[red]Erro de validação da transação: {e}[/red]")
            continue

        # --- Resumo pré-gravação ---
        table = Table(
            title="Lançamentos da Transação",
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
        )
        table.add_column("Conta", style="cyan")
        table.add_column("Débito", justify="right", style="green")
        table.add_column("Crédito", justify="right", style="red")
        table.add_column("Tags", style="dim")

        for p in t.postings:
            if p.amount > 0:
                debito, credito = str(p.amount), ""
            else:
                debito, credito = "", str(-p.amount)
            table.add_row(p.account, debito, credito, ", ".join(p.tags) if p.tags else "")

        console.print(Panel(
            table,
            title=f"[bold]{t.date} - {t.description}[/bold]",
            border_style="bright_blue",
            expand=False,
        ))

        transacao_finalizada = False

        if Confirm.ask("Deseja gravar esta transação no journal?", default=True):
            transactions.append(t)
            save_ledger(ledger_path, transactions)
            console.print("[green]Transação adicionada com sucesso.[/green]")
            transacao_finalizada = True
        else:
            action = questionary.select(
                "O que deseja fazer?",
                choices=[
                    ("Editar a transação", "edit"),
                    ("Descartar tudo", "discard"),
                    ("Salvar mesmo assim", "save"),
                ],
            ).ask()

            if action == "save":
                transactions.append(t)
                save_ledger(ledger_path, transactions)
                console.print("[green]Transação adicionada com sucesso.[/green]")
                transacao_finalizada = True
            elif action == "discard":
                console.print("[yellow]Transação descartada a pedido do usuário.[/yellow]")
                transacao_finalizada = True

        if transacao_finalizada:
            if Confirm.ask("Deseja adicionar outra transação?", default=False):
                continue
            console.print("[green]Até a próxima![/green]")
            return


@app.command()
def balance() -> None:
    """Exibe o balanço por conta."""
    ledger_path = get_ledger_path()
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
    ledger_path = get_ledger_path()
    transactions = load_ledger(ledger_path)
    recent = transactions[-limit:]

    table = Table(title=f"Últimas {limit} transações")
    table.add_column("Data", style="dim")
    table.add_column("Descrição", style="cyan")
    table.add_column("Lançamentos", style="green")
    for t in reversed(recent):
        postings_str = "; ".join(f"{p.account} {p.amount}" for p in t.postings)
        table.add_row(str(t.date), t.description, postings_str)
    console.print(table)


@app.command()
def mcp() -> None:
    """Inicia o servidor MCP via stdio."""
    import sys
    from homebeans.mcp_server import mcp as mcp_instance
    print("Starting HomeBeans MCP Server...", file=sys.stderr)
    mcp_instance.run()


def main() -> None:
    app()


if __name__ == "__main__":
    main()

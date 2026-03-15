"""Interface CLI com Typer e Rich."""

from pathlib import Path

import questionary
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table

from core.suggester import extract_all_accounts, suggest_for_description
from homebeans.models import Posting, Transaction
from homebeans.reports import balance_report
from homebeans.storage import load_ledger, save_ledger

load_dotenv()

app = typer.Typer(
    name="homebeans",
    help="Sistema de Contabilidade de Partida Dobrada inspirado no hledger.",
)
console = Console()


def _get_ledger_path() -> Path:
    import os
    path = os.getenv("LEDGER_PATH", "./data/ledger.yaml")
    return Path(path)


@app.command()
def add(
) -> None:
    """Adiciona uma transação ao livro-razão via wizard interativo."""
    from datetime import date, datetime
    from decimal import Decimal, InvalidOperation

    ledger_path = _get_ledger_path()
    console.print("[green]Tudo certo, vamos começar.[/green]")
    console.print(
        "[dim]Dica: use '<' para voltar ao passo anterior ou cancelar quando indicado.[/dim]"
    )
    console.print(
        "[dim]Dica: tags são palavras-chave livres, separadas por espaço ou vírgula (ex: familia brinquedos arthur).[/dim]"
    )

    # Checagem básica do journal antes de iniciar interação.
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
        # Estado inicial/valores padrão para permitir "editar" a transação.
        today_str = date.today().isoformat()
        dt: date | None = None
        description: str | None = None
        transaction_tags: list[str] = []
        postings_list: list[Posting] = []
        saldo = Decimal("0")
        is_first_posting = True

        # --- Pergunta: Data ---
        while dt is None:
            date_str = questionary.text(
                "Data (YYYY-MM-DD):",
                default=today_str,
            ).ask()
            if date_str is None:
                if Confirm.ask("Deseja sair sem salvar?", default=True):
                    console.print("[yellow]Operação cancelada.[/yellow]")
                    raise typer.Exit(0)
                continue
            date_str = date_str.strip()
            if date_str == "<":
                # Primeira pergunta: permite sair.
                if Confirm.ask("Deseja sair sem salvar?", default=True):
                    console.print("[yellow]Operação cancelada.[/yellow]")
                    raise typer.Exit(0)
                else:
                    continue
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                console.print(
                    f"[red]Data inválida: {date_str} (use YYYY-MM-DD)[/red]"
                )
                dt = None

        # --- Pergunta: Descrição ---
        while description is None:
            desc_input = questionary.text(
                "Descrição da transação:"
            ).ask()
            if desc_input is None:
                if Confirm.ask("Deseja sair sem salvar?", default=True):
                    console.print("[yellow]Operação cancelada.[/yellow]")
                    raise typer.Exit(0)
                continue
            desc_input = desc_input.strip()
            if desc_input == "<":
                # Volta para a data.
                dt = None
                # volta ao loop da data
                while dt is None:
                    date_str = questionary.text(
                        "Data (YYYY-MM-DD):",
                        default=today_str,
                    ).ask()
                    if date_str is None:
                        if Confirm.ask(
                            "Deseja sair sem salvar?", default=True
                        ):
                            console.print(
                                "[yellow]Operação cancelada.[/yellow]"
                            )
                            raise typer.Exit(0)
                        continue
                    date_str = date_str.strip()
                    if date_str == "<":
                        if Confirm.ask(
                            "Deseja sair sem salvar?", default=True
                        ):
                            console.print(
                                "[yellow]Operação cancelada.[/yellow]"
                            )
                            raise typer.Exit(0)
                        else:
                            continue
                    try:
                        dt = datetime.strptime(
                            date_str, "%Y-%m-%d"
                        ).date()
                    except ValueError:
                        console.print(
                            f"[red]Data inválida: {date_str} (use YYYY-MM-DD)[/red]"
                        )
                        dt = None
                # depois de voltar e corrigir data, pergunta descrição novamente
                continue

            if not desc_input:
                console.print("[red]Descrição não pode ser vazia.[/red]")
                continue
            description = desc_input

        # --- Pergunta: Tags da transação (opcional, uma vez) ---
        while True:
            tags_input = questionary.text(
                "Tags da transação (opcional, separadas por espaço ou vírgula):",
            ).ask()
            if tags_input is None:
                if Confirm.ask("Deseja sair sem salvar?", default=True):
                    console.print("[yellow]Operação cancelada.[/yellow]")
                    raise typer.Exit(0)
                continue
            tags_raw = tags_input.strip()
            if tags_raw == "<":
                # Volta para a descrição.
                description = None
                break

            transaction_tags = []
            if tags_raw:
                import re

                parts = re.split(r"[,\s]+", tags_raw)
                transaction_tags = [p.strip() for p in parts if p.strip()]
            break

        # Se descrição foi zerada por um backtracking nas tags, recomeça o fluxo.
        if description is None:
            continue

        # Sugestões com base na descrição preenchida.
        suggested_posting, suggested_amount = suggest_for_description(
            transactions, description
        )

        # --- Loop de lançamentos (postings) ---
        while True:
            console.print(f"[blue]Saldo atual da transação: {saldo}[/blue]")
            if saldo != 0:
                console.print(
                    f"[yellow]Falta {(-saldo)} para zerar.[/yellow]"
                )

            # Conta com autocomplete.
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
                if Confirm.ask(
                    "Cancelar esta transação?", default=True
                ):
                    console.print(
                        "[yellow]Transação cancelada pelo usuário.[/yellow]"
                    )
                    raise typer.Exit(0)
                # Se não cancelar, continua o loop.
                continue
            account = account.strip()
            if account == "<":
                # Volta para a descrição.
                description = None
                # Sai do loop de postings para voltar à descrição.
                break

            # Valor com sugestão.
            default_amount_str = ""
            if is_first_posting and suggested_amount is not None:
                default_amount_str = str(suggested_amount)
            elif saldo != 0:
                # Sugere o valor que fecharia a transação.
                default_amount_str = str(-saldo)

            amount_str = questionary.text(
                "Valor:",
                default=default_amount_str,
            ).ask()
            if amount_str is None:
                if Confirm.ask(
                    "Cancelar esta transação?", default=True
                ):
                    console.print(
                        "[yellow]Transação cancelada pelo usuário.[/yellow]"
                    )
                    raise typer.Exit(0)
                continue

            amount_str = amount_str.strip()
            if amount_str == "<":
                # Volta para a conta (não altera saldo nem postings).
                continue

            try:
                amount = Decimal(amount_str)
            except (InvalidOperation, ValueError):
                console.print(f"[red]Valor inválido: {amount_str}[/red]")
                continue

            try:
                posting = Posting(
                    account=account, amount=amount, tags=transaction_tags
                )
            except Exception as e:
                console.print(
                    f"[red]Erro de validação no lançamento: {e}[/red]"
                )
                continue

            postings_list.append(posting)
            saldo += posting.amount
            is_first_posting = False

            if saldo == 0:
                console.print("[green]Saldo da transação zerado.[/green]")
                break

        # Se descrição foi zerada por um backtracking, recomeça o fluxo.
        if description is None:
            continue

        # Validação final da transação com Pydantic.
        try:
            t = Transaction(
                date=dt, description=description, postings=postings_list
            )
        except Exception as e:
            console.print(
                f"[red]Erro de validação da transação: {e}[/red]"
            )
            # Volta ao início para permitir correção.
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
                debito = str(p.amount)
                credito = ""
            else:
                debito = ""
                credito = str(-p.amount)
            tags_str = ", ".join(p.tags) if p.tags else ""
            table.add_row(p.account, debito, credito, tags_str)

        panel = Panel(
            table,
            title=f"[bold]{t.date} - {t.description}[/bold]",
            border_style="bright_blue",
            expand=False,
        )
        console.print(panel)

        transacao_persistida_ou_descartada = False

        if Confirm.ask(
            "Deseja gravar esta transação no journal?", default=True
        ):
            transactions.append(t)
            save_ledger(ledger_path, transactions)
            console.print(
                "[green]Transação adicionada com sucesso.[/green]"
            )
            transacao_persistida_ou_descartada = True
        else:
            # Usuário respondeu "não" na confirmação.
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
                console.print(
                    "[green]Transação adicionada com sucesso.[/green]"
                )
                transacao_persistida_ou_descartada = True
            elif action == "discard":
                console.print(
                    "[yellow]Transação descartada a pedido do usuário.[/yellow]"
                )
                transacao_persistida_ou_descartada = True
            # action == "edit" -> recomeça o loop externo com a mesma base de histórico.
            # Isso permite refazer data, descrição e postings; sugestões continuam funcionando.
            # Loop externo continua sem marcar como finalizada.

        if transacao_persistida_ou_descartada:
            # Pergunta se o usuário quer iniciar outra transação inteira.
            if Confirm.ask(
                "Deseja adicionar outra transação?", default=False
            ):
                # volta ao início do while True externo
                continue
            console.print("[green]Até a próxima![/green]")
            return


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
    from homebeans.viz import export_balance_chart

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

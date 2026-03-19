import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from homebeans.models import Posting, Transaction
from homebeans.reports import balance_report
from homebeans.storage import load_ledger, save_ledger
from core.suggester import extract_all_accounts

load_dotenv()

mcp = FastMCP("homebeans")

def _get_ledger_path() -> Path:
    path = os.getenv("LEDGER_PATH", "./data/ledger.yaml")
    return Path(path)

@mcp.tool()
def get_balance() -> str:
    """Retorna o balanço financeiro atual agrupado por contas do aplicativo HomeBeans."""
    ledger_path = _get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    report = balance_report(transactions)
    if not report:
        return "Nenhuma conta possui saldo no momento."

    output = ["Balanço de Contas HomeBeans:"]
    for account, bal in report:
        output.append(f"- {account}: {bal}")
    return "\n".join(output)

@mcp.tool()
def get_transactions(limit: int = 10) -> str:
    """
    Retorna as transações mais recentes do ledger para análise.
    
    Args:
        limit (int): Número máximo de transações para retornar (padrão 10).
    """
    ledger_path = _get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Nenhuma transação registrada no momento."

    recent = transactions[-limit:]
    output = [f"Últimas {len(recent)} transações:"]
    for t in reversed(recent):
        postings_str = ", ".join(f"[{p.account}: {p.amount}]" for p in t.postings)
        output.append(f"Data: {t.date} | Desc: {t.description} | {postings_str}")
        
    return "\n".join(output)

@mcp.tool()
def add_transaction(date_str: str, description: str, postings: list[dict[str, Any]]) -> str:
    """
    Adiciona uma nova transação financeira ao ledger Homebeans.
    
    Args:
        date_str (str): A data da transação no formato YYYY-MM-DD.
        description (str): Descrição clara e concisa (ex: Compra de teclado novo).
        postings (list[dict]): Lista de dicionários representando os lançamentos por partida dobrada.
                               Ex: [{"account": "assets:bank", "amount": "-150.00"}, 
                                    {"account": "despesas:equipamento", "amount": "150.00"}]
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return "Erro: Data deve estar no formato YYYY-MM-DD."

    postings_list = []
    for p_dict in postings:
        if "account" not in p_dict or "amount" not in p_dict:
            return "Erro: Cada posting deve conter 'account' e 'amount'."
        try:
            amt = Decimal(str(p_dict["amount"]))
            posting = Posting(
                account=p_dict["account"], 
                amount=amt, 
                tags=p_dict.get("tags", [])
            )
            postings_list.append(posting)
        except Exception as e:
            return f"Erro na validação do posting {p_dict}: {e}"

    try:
        t = Transaction(date=dt, description=description, postings=postings_list)
    except Exception as e:
        return f"Erro na validação da transação (partida dobrada etc): {e}"

    ledger_path = _get_ledger_path()
    # Cria diretório caso não exista
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        transactions = load_ledger(ledger_path)
    except Exception:
        # Se falhou ler por outro motivo e já tivermos o ledger, inicializa nulo
        if ledger_path.exists():
            return "Erro: Falha ao carregar arquivo de ledger existente."
        transactions = []

    transactions.append(t)
    save_ledger(ledger_path, transactions)
    return f"Transação adicionada com sucesso em {date_str} - {description}."

@mcp.tool()
def get_accounts_tree() -> str:
    """Retorna a lista completa das contas contábeis organizadas por hierarquia atualmente em uso no HomeBeans."""
    ledger_path = _get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Nenhuma conta encontrada no ledger vazio."

    accounts = extract_all_accounts(transactions)
    if not accounts:
        return "Nenhuma conta foi utilizada ainda."

    output = ["Contas Financeiras Em Uso:"]
    for acc in accounts:
        output.append(f"- {acc}")
    return "\n".join(output)

@mcp.tool()
def delete_transaction(date_str: str, description: str) -> str:
    """
    Remove uma transação específica do ledger baseando-se na data (YYYY-MM-DD) e descrição exata (case-insensitive).
    Dica: use get_transactions primeiro para listar os registros recentes e obter a data e descrição corretas.
    
    Args:
        date_str (str): A data exata da transação (ex: 2024-01-15).
        description (str): A descrição da transação.
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return "Erro: Data deve estar no formato YYYY-MM-DD."

    ledger_path = _get_ledger_path()
    try:
        transactions = load_ledger(ledger_path)
    except Exception as e:
        return f"Erro ao carregar transações: {e}"

    if not transactions:
        return "Erro: Ledger está vazio."

    target_desc = description.strip().lower()
    matching_idx = -1
    
    # Busca a primeira transação que casa com data e descrição
    for i, t in enumerate(transactions):
        if t.date == dt and t.description.strip().lower() == target_desc:
            matching_idx = i
            break

    if matching_idx == -1:
        return f"Erro: Nenhuma transação encontrada no dia {date_str} com a descrição '{description}'."

    deleted = transactions.pop(matching_idx)
    save_ledger(ledger_path, transactions)
    return f"Transação '{deleted.description}' do dia {deleted.date} removida com sucesso."


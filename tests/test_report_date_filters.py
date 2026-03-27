"""Testes para filtros de data nos relatórios e na função filter_by_dates.

Cobre:
- filter_by_dates: sem filtro, só start, só end, intervalo, fora do intervalo
- get_income_statement: com e sem filtro de datas
- get_balance_sheet: com e sem filtro de datas
- get_cashflow: com e sem filtro de datas
- Data inválida nos 3 tools
- Período sem transações (filtro exclui tudo)

Todas as transações criadas aqui seguem partida dobrada (soma zero).
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from homebeans.models import Posting, Transaction
from homebeans.reports import filter_by_dates
from homebeans.mcp_server import get_income_statement, get_balance_sheet, get_cashflow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _posting(account: str, amount: str, tags=None) -> Posting:
    return Posting(account=account, amount=Decimal(amount), tags=tags or [])


def _tx(description: str, tx_date: date, postings: list[Posting]) -> Transaction:
    assert sum(p.amount for p in postings) == Decimal("0"), (
        f"Transação '{description}' desbalanceada."
    )
    return Transaction(date=tx_date, description=description, postings=postings)


# Transações espalhadas em 3 meses para testar os filtros
TRANSACTIONS = [
    _tx("Salário jan", date(2026, 1, 5), [
        _posting("ativos:banco", "5000.00"),
        _posting("entradas:salario", "-5000.00"),
    ]),
    _tx("Mercado jan", date(2026, 1, 20), [
        _posting("despesas:alimentacao", "300.00"),
        _posting("ativos:banco", "-300.00"),
    ]),
    _tx("Salário fev", date(2026, 2, 5), [
        _posting("ativos:banco", "5000.00"),
        _posting("entradas:salario", "-5000.00"),
    ]),
    _tx("Aluguel fev", date(2026, 2, 10), [
        _posting("despesas:moradia:aluguel", "1500.00"),
        _posting("ativos:banco", "-1500.00"),
    ]),
    _tx("Salário mar", date(2026, 3, 5), [
        _posting("ativos:banco", "5000.00"),
        _posting("entradas:salario", "-5000.00"),
    ]),
    _tx("Internet mar", date(2026, 3, 15), [
        _posting("despesas:moradia:internet", "100.00"),
        _posting("ativos:banco", "-100.00"),
    ]),
]


def _mock_load(txs):
    return patch("homebeans.mcp_server.load_ledger", return_value=txs)


# ---------------------------------------------------------------------------
# filter_by_dates (unitário — sem mock, testa a função diretamente)
# ---------------------------------------------------------------------------

def test_filter_sem_datas_retorna_tudo():
    result = filter_by_dates(TRANSACTIONS)
    assert len(result) == 6


def test_filter_so_start_date():
    result = filter_by_dates(TRANSACTIONS, start_date=date(2026, 2, 1))
    assert all(t.date >= date(2026, 2, 1) for t in result)
    assert len(result) == 4  # fev (2) + mar (2)


def test_filter_so_end_date():
    result = filter_by_dates(TRANSACTIONS, end_date=date(2026, 1, 31))
    assert all(t.date <= date(2026, 1, 31) for t in result)
    assert len(result) == 2  # só jan


def test_filter_intervalo():
    result = filter_by_dates(
        TRANSACTIONS,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 28),
    )
    assert len(result) == 2
    assert all(t.date.month == 2 for t in result)


def test_filter_extremos_inclusivos():
    """Os limites start e end devem ser inclusivos."""
    result = filter_by_dates(
        TRANSACTIONS,
        start_date=date(2026, 1, 5),   # exatamente o dia do Salário jan
        end_date=date(2026, 1, 5),
    )
    assert len(result) == 1
    assert result[0].description == "Salário jan"


def test_filter_sem_resultado():
    result = filter_by_dates(
        TRANSACTIONS,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )
    assert result == []


# ---------------------------------------------------------------------------
# get_income_statement
# ---------------------------------------------------------------------------

def test_income_statement_sem_filtro():
    with _mock_load(TRANSACTIONS):
        result = get_income_statement(period="month")
    # Todos os 3 meses devem aparecer
    assert "2026-01" in result
    assert "2026-02" in result
    assert "2026-03" in result


def test_income_statement_com_start_date():
    with _mock_load(TRANSACTIONS):
        result = get_income_statement(period="month", start_date="2026-02-01")
    assert "2026-01" not in result
    assert "2026-02" in result
    assert "2026-03" in result


def test_income_statement_com_intervalo():
    with _mock_load(TRANSACTIONS):
        result = get_income_statement(period="month", start_date="2026-02-01", end_date="2026-02-28")
    assert "2026-01" not in result
    assert "2026-02" in result
    assert "2026-03" not in result


def test_income_statement_data_invalida():
    with _mock_load(TRANSACTIONS):
        result = get_income_statement(start_date="32/01/2026")
    assert "Erro" in result


def test_income_statement_periodo_vazio():
    with _mock_load(TRANSACTIONS):
        result = get_income_statement(start_date="2025-01-01", end_date="2025-12-31")
    assert "Nenhuma transação" in result


# ---------------------------------------------------------------------------
# get_balance_sheet
# ---------------------------------------------------------------------------

def test_balance_sheet_sem_filtro():
    with _mock_load(TRANSACTIONS):
        result = get_balance_sheet(period="month")
    assert "2026-01" in result
    assert "2026-03" in result


def test_balance_sheet_com_end_date():
    with _mock_load(TRANSACTIONS):
        result = get_balance_sheet(period="month", end_date="2026-01-31")
    assert "2026-01" in result
    assert "2026-02" not in result


def test_balance_sheet_data_invalida():
    with _mock_load(TRANSACTIONS):
        result = get_balance_sheet(start_date="nao-e-data")
    assert "Erro" in result


# ---------------------------------------------------------------------------
# get_cashflow
# ---------------------------------------------------------------------------

def test_cashflow_sem_filtro():
    with _mock_load(TRANSACTIONS):
        result = get_cashflow(period="month")
    assert "2026-01" in result
    assert "2026-02" in result
    assert "2026-03" in result


def test_cashflow_com_intervalo():
    with _mock_load(TRANSACTIONS):
        result = get_cashflow(period="month", start_date="2026-03-01", end_date="2026-03-31")
    assert "2026-01" not in result
    assert "2026-02" not in result
    assert "2026-03" in result


def test_cashflow_data_invalida():
    with _mock_load(TRANSACTIONS):
        result = get_cashflow(end_date="99-99-9999")
    assert "Erro" in result

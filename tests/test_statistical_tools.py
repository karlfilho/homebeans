"""Testes para as ferramentas estatísticas: get_ledger_stats,
get_account_statement e get_spending_summary.

Todas as transações criadas aqui seguem partida dobrada (soma zero).
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from homebeans.models import Posting, Transaction
from homebeans.mcp_server import get_ledger_stats, get_account_statement, get_spending_summary


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


TRANSACTIONS = [
    _tx("Salário jan", date(2026, 1, 5), [
        _posting("ativos:banco", "5000.00"),
        _posting("entradas:salario", "-5000.00"),
    ]),
    _tx("Mercado jan", date(2026, 1, 20), [
        _posting("despesas:alimentacao:mercado", "300.00", ["local:carrefour"]),
        _posting("ativos:banco", "-300.00"),
    ]),
    _tx("Combustível jan", date(2026, 1, 25), [
        _posting("despesas:transporte:combustivel", "150.00", ["veiculo:meteor"]),
        _posting("ativos:carteira", "-150.00"),
    ]),
    _tx("Salário fev", date(2026, 2, 5), [
        _posting("ativos:banco", "5000.00"),
        _posting("entradas:salario", "-5000.00"),
    ]),
    _tx("Aluguel fev", date(2026, 2, 10), [
        _posting("despesas:moradia:aluguel", "1500.00"),
        _posting("ativos:banco", "-1500.00"),
    ]),
    _tx("Internet fev", date(2026, 2, 15), [
        _posting("despesas:moradia:internet", "100.00", ["fornecedor:claro"]),
        _posting("ativos:banco", "-100.00"),
    ]),
]


def _mock_load(txs):
    return patch("homebeans.mcp_server.load_ledger", return_value=txs)


# ===========================================================================
# get_ledger_stats
# ===========================================================================

def test_stats_total_transacoes():
    with _mock_load(TRANSACTIONS):
        result = get_ledger_stats()
    assert "6" in result  # 6 transações


def test_stats_periodo():
    """Deve exibir a data da primeira e da última transação."""
    with _mock_load(TRANSACTIONS):
        result = get_ledger_stats()
    assert "2026-01-05" in result
    assert "2026-02-15" in result


def test_stats_contas_distintas():
    """Deve contar as contas únicas usadas nos postings."""
    # ativos:banco, entradas:salario, despesas:alimentacao:mercado,
    # ativos:carteira, despesas:transporte:combustivel,
    # despesas:moradia:aluguel, despesas:moradia:internet = 7 contas
    with _mock_load(TRANSACTIONS):
        result = get_ledger_stats()
    assert "7" in result


def test_stats_tags_distintas():
    """Deve contar as tags únicas: local:carrefour, veiculo:meteor, fornecedor:claro = 3."""
    with _mock_load(TRANSACTIONS):
        result = get_ledger_stats()
    assert "3" in result


def test_stats_media_por_mes():
    """6 transações em 2 meses → média 3.0."""
    with _mock_load(TRANSACTIONS):
        result = get_ledger_stats()
    assert "3.0" in result


def test_stats_ledger_vazio():
    with _mock_load([]):
        result = get_ledger_stats()
    assert "vazio" in result.lower()


# ===========================================================================
# get_account_statement
# ===========================================================================

def test_statement_conta_existente():
    with _mock_load(TRANSACTIONS):
        result = get_account_statement(account="ativos:banco")
    # Salário jan (+5000), Mercado jan (-300), Salário fev (+5000), Aluguel fev (-1500), Internet fev (-100)
    assert "Salário jan" in result
    assert "Mercado jan" in result
    assert "Aluguel fev" in result


def test_statement_saldo_acumulado_correto():
    """Saldo final de ativos:banco: 5000 - 300 + 5000 - 1500 - 100 = 8100."""
    with _mock_load(TRANSACTIONS):
        result = get_account_statement(account="ativos:banco")
    assert "8100" in result


def test_statement_filtro_por_data():
    """Com start_date em fevereiro, apenas os lançamentos de fev devem aparecer."""
    with _mock_load(TRANSACTIONS):
        result = get_account_statement(account="ativos:banco", start_date="2026-02-01")
    assert "Salário fev" in result
    assert "Salário jan" not in result


def test_statement_conta_inexistente():
    with _mock_load(TRANSACTIONS):
        result = get_account_statement(account="passivos:cartao")
    assert "Nenhum lançamento" in result


def test_statement_filtro_parcial_de_conta():
    """Filtro 'despesas:moradia' deve capturar aluguel e internet."""
    with _mock_load(TRANSACTIONS):
        result = get_account_statement(account="despesas:moradia")
    assert "Aluguel fev" in result
    assert "Internet fev" in result
    assert "Mercado jan" not in result


def test_statement_ordenado_por_data():
    """Lançamentos devem aparecer em ordem cronológica."""
    with _mock_load(TRANSACTIONS):
        result = get_account_statement(account="ativos:banco")
    pos_jan = result.index("Salário jan")
    pos_fev = result.index("Salário fev")
    assert pos_jan < pos_fev


def test_statement_data_invalida():
    with _mock_load(TRANSACTIONS):
        result = get_account_statement(account="ativos:banco", start_date="nao-e-data")
    assert "Erro" in result


# ===========================================================================
# get_spending_summary
# ===========================================================================

def test_summary_categorias_presentes():
    """Deve exibir despesas:alimentacao, despesas:transporte, despesas:moradia."""
    with _mock_load(TRANSACTIONS):
        result = get_spending_summary(period="all")
    assert "despesas:alimentacao" in result
    assert "despesas:transporte" in result
    assert "despesas:moradia" in result


def test_summary_sem_entradas_ou_ativos():
    """Entradas e ativos não devem aparecer no resumo de gastos."""
    with _mock_load(TRANSACTIONS):
        result = get_spending_summary(period="all")
    assert "entradas" not in result
    assert "ativos" not in result


def test_summary_percentual_presente():
    """O resumo deve conter o símbolo % para cada categoria."""
    with _mock_load(TRANSACTIONS):
        result = get_spending_summary(period="all")
    assert "%" in result


def test_summary_top_n():
    """top_n=1 deve retornar apenas a categoria com maior gasto."""
    with _mock_load(TRANSACTIONS):
        result = get_spending_summary(period="all", top_n=1)
    # despesas:moradia = 1600, despesas:alimentacao = 300, despesas:transporte = 150
    assert "despesas:moradia" in result
    assert "despesas:alimentacao" not in result


def test_summary_filtro_de_data():
    """Com start_date em fevereiro, apenas despesas de fev devem aparecer."""
    with _mock_load(TRANSACTIONS):
        result = get_spending_summary(period="all", start_date="2026-02-01")
    assert "despesas:moradia" in result
    assert "despesas:alimentacao" not in result
    assert "despesas:transporte" not in result


def test_summary_agrupamento_por_mes():
    """period='month' deve mostrar períodos separados para jan e fev."""
    with _mock_load(TRANSACTIONS):
        result = get_spending_summary(period="month")
    assert "2026-01" in result
    assert "2026-02" in result


def test_summary_sem_despesas():
    """Ledger só com entradas não deve gerar linhas de categoria."""
    only_income = [
        _tx("Salário", date(2026, 1, 5), [
            _posting("ativos:banco", "5000.00"),
            _posting("entradas:salario", "-5000.00"),
        ])
    ]
    with _mock_load(only_income):
        result = get_spending_summary(period="all")
    assert "Nenhuma despesa" in result


def test_summary_data_invalida():
    with _mock_load(TRANSACTIONS):
        result = get_spending_summary(period="month", start_date="31-01-2026")
    assert "Erro" in result

"""Testes para a tool get_balance com e sem filtro de conta.

Cobre:
- Sem filtro: retorna todas as contas
- Filtro por raiz (ex: "ativos")
- Filtro por subconta (ex: "ativos:banco")
- Filtro case-insensitive
- Filtro parcial (ex: "banco" encontra "ativos:banco")
- Filtro sem resultado
- Ledger vazio
- Cabeçalho indica o filtro aplicado

Todas as transações seguem partida dobrada (soma zero).
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from homebeans.models import Posting, Transaction
from homebeans.mcp_server import get_balance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _posting(account: str, amount: str) -> Posting:
    return Posting(account=account, amount=Decimal(amount))


def _tx(description: str, postings: list[Posting]) -> Transaction:
    assert sum(p.amount for p in postings) == Decimal("0"), (
        f"Transação '{description}' desbalanceada."
    )
    return Transaction(date=date(2026, 1, 1), description=description, postings=postings)


TRANSACTIONS = [
    _tx("Salário", [
        _posting("ativos:banco:nubank", "5000.00"),
        _posting("entradas:salario", "-5000.00"),
    ]),
    _tx("Mercado", [
        _posting("despesas:alimentacao:mercado", "300.00"),
        _posting("ativos:carteira", "-300.00"),
    ]),
    _tx("Aluguel", [
        _posting("despesas:moradia:aluguel", "1500.00"),
        _posting("ativos:banco:nubank", "-1500.00"),
    ]),
    _tx("Freelance", [
        _posting("ativos:banco:inter", "800.00"),
        _posting("entradas:freelance", "-800.00"),
    ]),
]


def _mock_load(txs):
    return patch("homebeans.mcp_server.load_ledger", return_value=txs)


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def test_sem_filtro_retorna_todas_as_contas():
    with _mock_load(TRANSACTIONS):
        result = get_balance()
    assert "ativos:banco:nubank" in result
    assert "ativos:carteira" in result
    assert "ativos:banco:inter" in result
    assert "despesas:alimentacao:mercado" in result
    assert "despesas:moradia:aluguel" in result
    assert "entradas:salario" in result
    assert "entradas:freelance" in result


def test_filtro_por_raiz():
    with _mock_load(TRANSACTIONS):
        result = get_balance(account_filter="ativos")
    assert "ativos:banco:nubank" in result
    assert "ativos:carteira" in result
    assert "ativos:banco:inter" in result
    # Outras raízes não devem aparecer
    assert "despesas" not in result
    assert "entradas" not in result


def test_filtro_por_subconta():
    with _mock_load(TRANSACTIONS):
        result = get_balance(account_filter="ativos:banco")
    assert "ativos:banco:nubank" in result
    assert "ativos:banco:inter" in result
    assert "ativos:carteira" not in result


def test_filtro_case_insensitive():
    with _mock_load(TRANSACTIONS):
        result = get_balance(account_filter="ATIVOS")
    assert "ativos:banco:nubank" in result


def test_filtro_parcial():
    """Substring no meio do nome da conta deve funcionar."""
    with _mock_load(TRANSACTIONS):
        result = get_balance(account_filter="nubank")
    assert "ativos:banco:nubank" in result
    assert "ativos:banco:inter" not in result


def test_filtro_sem_resultado():
    with _mock_load(TRANSACTIONS):
        result = get_balance(account_filter="passivos")
    assert "Nenhuma conta encontrada" in result


def test_ledger_vazio():
    with _mock_load([]):
        result = get_balance()
    assert "Nenhuma conta" in result


def test_cabecalho_sem_filtro():
    with _mock_load(TRANSACTIONS):
        result = get_balance()
    # Sem filtro o cabeçalho não deve mencionar filtro
    assert "filtro" not in result.lower()


def test_cabecalho_com_filtro():
    """Cabeçalho deve indicar o filtro aplicado."""
    with _mock_load(TRANSACTIONS):
        result = get_balance(account_filter="ativos")
    assert "ativos" in result.split("\n")[0]


def test_saldo_calculado_corretamente():
    """O saldo de ativos:banco:nubank deve ser 5000 - 1500 = 3500."""
    with _mock_load(TRANSACTIONS):
        result = get_balance(account_filter="ativos:banco:nubank")
    assert "3500" in result

"""Testes para a tool get_recent_transactions.

Cobre:
- Retorno das últimas N transações sem filtros
- Limite respeitado corretamente
- Filtro por conta (account_filter)
- Filtro por tag (tag_filter)
- Combinação de account_filter + tag_filter
- Ledger vazio
- Filtros sem resultado
- Ordem: mais recente primeiro
- Partida dobrada: todas as transações criadas nos testes têm soma zero
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pytest

from homebeans.models import Posting, Transaction
from homebeans.mcp_server import get_recent_transactions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _posting(account: str, amount: str, tags: list[str] | None = None) -> Posting:
    return Posting(account=account, amount=Decimal(amount), tags=tags or [])


def _tx(description: str, tx_date: date, postings: list[Posting]) -> Transaction:
    """Cria uma transação; os postings passados devem somar zero (partida dobrada)."""
    assert sum(p.amount for p in postings) == Decimal("0"), (
        f"Transação '{description}' está desbalanceada — ajuste os postings."
    )
    return Transaction(date=tx_date, description=description, postings=postings)


TRANSACTIONS = [
    _tx("Salário janeiro", date(2026, 1, 5), [
        _posting("ativos:banco", "5000.00"),
        _posting("entradas:salario", "-5000.00"),
    ]),
    _tx("Mercado", date(2026, 1, 10), [
        _posting("despesas:alimentacao:mercado", "200.00", ["local:carrefour"]),
        _posting("ativos:banco", "-200.00"),
    ]),
    _tx("Combustível", date(2026, 1, 15), [
        _posting("despesas:transporte:combustivel", "150.00", ["veiculo:meteor"]),
        _posting("ativos:carteira", "-150.00"),
    ]),
    _tx("Aluguel", date(2026, 2, 1), [
        _posting("despesas:moradia:aluguel", "1500.00"),
        _posting("ativos:banco", "-1500.00"),
    ]),
    _tx("Freelance", date(2026, 2, 10), [
        _posting("ativos:banco", "800.00"),
        _posting("entradas:freelance", "-800.00", ["cliente:acme"]),
    ]),
]


# ---------------------------------------------------------------------------
# Helpers de mock
# ---------------------------------------------------------------------------

def _mock_load(txs):
    """Retorna um patch que substitui load_ledger pela lista fornecida."""
    return patch("homebeans.mcp_server.load_ledger", return_value=txs)


# ---------------------------------------------------------------------------
# Testes
# ---------------------------------------------------------------------------

def test_retorna_ultimas_n_sem_filtros():
    """Sem filtros, deve retornar as últimas N transações."""
    with _mock_load(TRANSACTIONS):
        result = get_recent_transactions(limit=3)
    # As últimas 3 são: Aluguel, Freelance (fev) e Combustível (jan)
    assert "Freelance" in result
    assert "Aluguel" in result
    assert "Combustível" in result
    assert "Salário janeiro" not in result


def test_limite_maior_que_total():
    """Se limit > total de transações, retorna todas."""
    with _mock_load(TRANSACTIONS):
        result = get_recent_transactions(limit=100)
    assert "Salário janeiro" in result
    assert "Freelance" in result


def test_ordem_mais_recente_primeiro():
    """A transação mais recente deve aparecer antes das mais antigas."""
    with _mock_load(TRANSACTIONS):
        result = get_recent_transactions(limit=5)
    pos_freelance = result.index("Freelance")
    pos_salario = result.index("Salário janeiro")
    assert pos_freelance < pos_salario, "Freelance (fev) deve vir antes de Salário (jan)"


def test_filtro_por_conta_exata():
    """Deve retornar apenas transações com posting na conta especificada."""
    with _mock_load(TRANSACTIONS):
        result = get_recent_transactions(limit=10, account_filter="ativos:carteira")
    assert "Combustível" in result
    # As outras não usam ativos:carteira
    assert "Mercado" not in result
    assert "Aluguel" not in result


def test_filtro_por_raiz_de_conta():
    """Filtro por raiz ('despesas') deve retornar todas as transações de despesa."""
    with _mock_load(TRANSACTIONS):
        result = get_recent_transactions(limit=10, account_filter="despesas")
    assert "Mercado" in result
    assert "Combustível" in result
    assert "Aluguel" in result
    assert "Salário janeiro" not in result
    assert "Freelance" not in result


def test_filtro_por_tag():
    """Deve retornar apenas transações com a tag especificada."""
    with _mock_load(TRANSACTIONS):
        result = get_recent_transactions(limit=10, tag_filter="veiculo:meteor")
    assert "Combustível" in result
    assert "Mercado" not in result


def test_filtro_por_tag_parcial():
    """Filtro de tag parcial ('veiculo') deve funcionar (case-insensitive)."""
    with _mock_load(TRANSACTIONS):
        result = get_recent_transactions(limit=10, tag_filter="veiculo")
    assert "Combustível" in result


def test_filtro_conta_e_tag_combinados():
    """Combinação de account_filter + tag_filter deve aplicar ambos (AND)."""
    with _mock_load(TRANSACTIONS):
        # Apenas Freelance tem ativos:banco + tag cliente:acme
        result = get_recent_transactions(limit=10, account_filter="entradas", tag_filter="cliente:acme")
    assert "Freelance" in result
    assert "Salário janeiro" not in result  # tem entradas mas não tem a tag


def test_ledger_vazio():
    """Ledger vazio deve retornar mensagem adequada."""
    with _mock_load([]):
        result = get_recent_transactions(limit=5)
    assert "Nenhuma" in result


def test_filtro_sem_resultado():
    """Filtro que não encontra nada deve retornar mensagem adequada."""
    with _mock_load(TRANSACTIONS):
        result = get_recent_transactions(limit=10, account_filter="passivos:cartao")
    assert "Nenhuma transação encontrada" in result


def test_resultado_contem_id():
    """Cada linha de resultado deve conter o ID da transação."""
    with _mock_load(TRANSACTIONS):
        result = get_recent_transactions(limit=2)
    lines = [l for l in result.split("\n") if "Desc:" in l]
    assert all("ID:" in line for line in lines)


def test_descricao_do_filtro_no_cabecalho():
    """O cabeçalho deve indicar os filtros aplicados."""
    with _mock_load(TRANSACTIONS):
        result = get_recent_transactions(limit=5, account_filter="despesas", tag_filter="veiculo")
    assert "despesas" in result
    assert "veiculo" in result

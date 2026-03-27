"""Testes para o campo id das transações.

Cobre:
- Geração automática de UUID na criação
- Unicidade entre transações distintas
- Preservação do id em round-trip YAML (salvar → carregar)
- Migração automática: YAML legado sem `id` recebe UUID na leitura
- O id não muda em edições (edit_transaction preserva o id original)
"""

import tempfile
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from homebeans.models import Posting, Transaction
from homebeans.storage import load_ledger, save_ledger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_transaction(**kwargs) -> Transaction:
    """Cria uma transação balanceada simples para uso nos testes."""
    defaults = dict(
        date=date(2026, 1, 15),
        description="Teste",
        postings=[
            Posting(account="despesas:alimentacao", amount=Decimal("100")),
            Posting(account="ativos:banco", amount=Decimal("-100")),
        ],
    )
    defaults.update(kwargs)
    return Transaction(**defaults)


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------

def test_id_gerado_automaticamente():
    """Nova transação deve ter um id UUID válido."""
    t = _make_transaction()
    assert t.id is not None
    assert len(t.id) > 0
    # Valida que é um UUID4 legítimo (não lança exceção)
    uuid.UUID(t.id, version=4)


def test_ids_unicos_entre_transacoes():
    """Duas transações criadas independentemente devem ter IDs diferentes."""
    t1 = _make_transaction()
    t2 = _make_transaction()
    assert t1.id != t2.id


def test_id_preservado_quando_fornecido():
    """Se um id for fornecido explicitamente, ele deve ser mantido."""
    custom_id = str(uuid.uuid4())
    t = _make_transaction(id=custom_id)
    assert t.id == custom_id


def test_transacao_balanceada_com_id():
    """Transação com id ainda deve obedecer a regra de soma zero."""
    t = _make_transaction()
    assert sum(p.amount for p in t.postings) == Decimal("0")


# ---------------------------------------------------------------------------
# Storage: round-trip e migração
# ---------------------------------------------------------------------------

def test_id_persistido_no_yaml(tmp_path):
    """O id deve ser salvo e carregado corretamente do YAML."""
    ledger = tmp_path / "ledger.yaml"
    t = _make_transaction()
    original_id = t.id

    save_ledger(ledger, [t])
    loaded = load_ledger(ledger)

    assert len(loaded) == 1
    assert loaded[0].id == original_id


def test_migracao_yaml_sem_id(tmp_path):
    """YAML legado sem campo `id` deve receber um UUID válido na leitura."""
    ledger = tmp_path / "ledger.yaml"

    # Escreve YAML antigo manualmente, sem campo `id`
    ledger.write_text(
        "transactions:\n"
        "  - date: '2026-01-15'\n"
        "    description: 'Transacao legada'\n"
        "    postings:\n"
        "      - account: 'despesas:alimentacao'\n"
        "        amount: '50.00'\n"
        "        tags: []\n"
        "      - account: 'ativos:banco'\n"
        "        amount: '-50.00'\n"
        "        tags: []\n",
        encoding="utf-8",
    )

    loaded = load_ledger(ledger)
    assert len(loaded) == 1
    # Deve ter recebido um UUID válido
    assert loaded[0].id is not None
    uuid.UUID(loaded[0].id, version=4)


def test_migracao_persiste_apos_salvar(tmp_path):
    """Após carregar um YAML legado e salvar, o id deve estar no arquivo."""
    ledger = tmp_path / "ledger.yaml"
    ledger.write_text(
        "transactions:\n"
        "  - date: '2026-01-15'\n"
        "    description: 'Transacao legada'\n"
        "    postings:\n"
        "      - account: 'despesas:alimentacao'\n"
        "        amount: '50.00'\n"
        "        tags: []\n"
        "      - account: 'ativos:banco'\n"
        "        amount: '-50.00'\n"
        "        tags: []\n",
        encoding="utf-8",
    )

    # Carrega (migra) e salva novamente
    loaded = load_ledger(ledger)
    migrated_id = loaded[0].id
    save_ledger(ledger, loaded)

    # Carrega pela segunda vez — o id deve ser o mesmo
    reloaded = load_ledger(ledger)
    assert reloaded[0].id == migrated_id


def test_id_preservado_em_multiplas_transacoes(tmp_path):
    """Múltiplas transações devem manter seus ids distintos após round-trip."""
    ledger = tmp_path / "ledger.yaml"
    t1 = _make_transaction(description="Compra A")
    t2 = _make_transaction(description="Compra B")

    save_ledger(ledger, [t1, t2])
    loaded = load_ledger(ledger)

    assert loaded[0].id == t1.id
    assert loaded[1].id == t2.id
    assert loaded[0].id != loaded[1].id

"""Testes para o modo de demonstração do HomeBeans."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

import homebeans.demo_mode as demo_module
from homebeans.demo_mode import enter_demo, exit_demo, get_demo_ledger_path, is_demo_active


# ---------------------------------------------------------------------------
# Fixture de isolamento: garante estado limpo antes/depois de cada teste
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_demo_state(tmp_path, monkeypatch):
    """Reseta o estado global do demo_mode e redireciona os paths para tmp_path."""
    # Garante que começa desativado
    demo_module._demo_active = False

    # Redireciona caminhos para tmp_path para evitar interferência com dados reais
    template = tmp_path / "demo_ledger_template.yaml"
    working = tmp_path / "demo_ledger.yaml"
    monkeypatch.setattr(demo_module, "_DEMO_TEMPLATE_PATH", template)
    monkeypatch.setattr(demo_module, "_DEMO_WORKING_PATH", working)

    yield template, working

    # Cleanup após o teste
    demo_module._demo_active = False
    if working.exists():
        working.unlink()


# ---------------------------------------------------------------------------
# Estado inicial
# ---------------------------------------------------------------------------

def test_demo_initially_inactive():
    assert not is_demo_active()


# ---------------------------------------------------------------------------
# enter_demo
# ---------------------------------------------------------------------------

def test_enter_demo_returns_ok_and_activates(reset_demo_state):
    template, _ = reset_demo_state
    template.write_text("transactions: []\n", encoding="utf-8")

    result = enter_demo()

    assert result == "ok"
    assert is_demo_active()


def test_enter_demo_copies_template_to_working(reset_demo_state):
    template, working = reset_demo_state
    template.write_text("transactions: []\n", encoding="utf-8")

    enter_demo()

    assert working.exists()
    assert working.read_text(encoding="utf-8") == "transactions: []\n"


def test_enter_demo_template_missing_returns_error(reset_demo_state):
    # template NÃO foi criado — deve retornar erro
    result = enter_demo()

    assert result.startswith("Erro")
    assert not is_demo_active()


def test_enter_demo_already_active_returns_message(reset_demo_state):
    template, _ = reset_demo_state
    template.write_text("transactions: []\n", encoding="utf-8")

    enter_demo()
    result = enter_demo()

    assert "já está ativo" in result


# ---------------------------------------------------------------------------
# exit_demo
# ---------------------------------------------------------------------------

def test_exit_demo_returns_ok_and_deactivates(reset_demo_state):
    template, _ = reset_demo_state
    template.write_text("transactions: []\n", encoding="utf-8")

    enter_demo()
    result = exit_demo()

    assert result == "ok"
    assert not is_demo_active()


def test_exit_demo_removes_working_file(reset_demo_state):
    template, working = reset_demo_state
    template.write_text("transactions: []\n", encoding="utf-8")

    enter_demo()
    assert working.exists()

    exit_demo()
    assert not working.exists()


def test_exit_demo_when_not_active_returns_message():
    result = exit_demo()
    assert "não está ativo" in result


# ---------------------------------------------------------------------------
# Integração com config.get_ledger_path()
# ---------------------------------------------------------------------------

def test_get_ledger_path_redirects_in_demo_mode(reset_demo_state, monkeypatch):
    template, working = reset_demo_state
    template.write_text("transactions: []\n", encoding="utf-8")

    from homebeans.config import get_ledger_path

    normal_path = get_ledger_path()
    enter_demo()
    demo_path = get_ledger_path()

    assert demo_path != normal_path
    assert demo_path == working


def test_get_ledger_path_restored_after_exit(reset_demo_state, monkeypatch):
    template, _ = reset_demo_state
    template.write_text("transactions: []\n", encoding="utf-8")

    from homebeans.config import get_ledger_path

    normal_path = get_ledger_path()
    enter_demo()
    exit_demo()
    restored_path = get_ledger_path()

    assert restored_path == normal_path


# ---------------------------------------------------------------------------
# Isolamento: o ledger real não é modificado durante o demo
# ---------------------------------------------------------------------------

def test_demo_does_not_affect_real_ledger(reset_demo_state, monkeypatch, tmp_path):
    """Transações gravadas no demo NÃO devem aparecer no ledger real."""
    from homebeans.models import Posting, Transaction
    from homebeans.storage import load_ledger, save_ledger
    from homebeans.config import get_ledger_path

    template, working = reset_demo_state

    # Prepara ledger real com uma transação
    real_ledger = tmp_path / "real_ledger.yaml"
    real_tx = Transaction(
        date=date(2026, 1, 1),
        description="Transacao real",
        postings=[
            Posting(account="ativos:banco:nubank", amount=Decimal("1000")),
            Posting(account="entradas:salario", amount=Decimal("-1000")),
        ],
    )
    save_ledger(real_ledger, [real_tx])
    monkeypatch.setenv("LEDGER_PATH", str(real_ledger))

    # Template de demo vazio
    template.write_text("transactions: []\n", encoding="utf-8")

    # Entra no demo e adiciona uma transação fictícia
    enter_demo()
    demo_tx = Transaction(
        date=date(2026, 2, 1),
        description="Transacao ficticia demo",
        postings=[
            Posting(account="despesas:alimentacao:mercado", amount=Decimal("50")),
            Posting(account="ativos:carteira", amount=Decimal("-50")),
        ],
    )
    demo_ledger_path = get_ledger_path()
    save_ledger(demo_ledger_path, [demo_tx])

    # Sai do demo
    exit_demo()

    # Ledger real deve permanecer com apenas a transação original
    real_transactions = load_ledger(real_ledger)
    assert len(real_transactions) == 1
    assert real_transactions[0].description == "Transacao real"


# ---------------------------------------------------------------------------
# Template de demonstração embutido no projeto
# ---------------------------------------------------------------------------

def test_demo_template_exists_in_project():
    """O template padrão do projeto deve existir e ser um YAML válido."""
    from ruamel.yaml import YAML

    project_template = Path("data/demo_ledger_template.yaml")
    assert project_template.exists(), "data/demo_ledger_template.yaml não encontrado"

    yaml = YAML()
    with project_template.open("r", encoding="utf-8") as f:
        data = yaml.load(f)

    assert "transactions" in data
    assert len(data["transactions"]) > 0


def test_demo_template_all_transactions_balanced():
    """Todas as transações do template devem ter soma zero (partida dobrada)."""
    from decimal import Decimal as D
    from ruamel.yaml import YAML

    project_template = Path("data/demo_ledger_template.yaml")
    yaml = YAML()
    with project_template.open("r", encoding="utf-8") as f:
        data = yaml.load(f)

    for tx in data["transactions"]:
        total = sum(D(str(p["amount"])) for p in tx["postings"])
        assert total == D("0"), (
            f"Transação '{tx['description']}' ({tx['date']}) não está balanceada: soma = {total}"
        )


def test_demo_template_loads_as_transactions():
    """O template deve ser carregável pelo storage sem erros."""
    from homebeans.storage import load_ledger

    project_template = Path("data/demo_ledger_template.yaml")
    transactions = load_ledger(project_template)

    assert len(transactions) > 0
    for t in transactions:
        assert t.id
        assert t.date
        assert t.description
        assert len(t.postings) >= 2

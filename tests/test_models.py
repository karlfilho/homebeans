"""Testes de integridade dos modelos de partida dobrada."""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from homebeans.models import Posting, Transaction


def test_transaction_balanced_accepted():
    """Transação balanceada (ex: +100, -100) é aceita."""
    t = Transaction(
        date=date(2024, 1, 1),
        description="Venda",
        postings=[
            Posting(account="assets:bank", amount=Decimal("100")),
            Posting(account="income:sales", amount=Decimal("-100")),
        ],
    )
    assert len(t.postings) == 2
    assert sum(p.amount for p in t.postings) == 0


def test_transaction_unbalanced_raises():
    """Transação desbalanceada levanta ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        Transaction(
            date=date(2024, 1, 1),
            description="Venda inválida",
            postings=[
                Posting(account="assets:bank", amount=Decimal("100")),
                Posting(account="income:sales", amount=Decimal("-50")),
            ],
        )
    assert "desbalanceada" in str(exc_info.value)


def test_transaction_single_posting_rejected():
    """Transação com um único posting é rejeitada."""
    with pytest.raises(ValidationError) as exc_info:
        Transaction(
            date=date(2024, 1, 1),
            description="Único posting",
            postings=[
                Posting(account="assets:bank", amount=Decimal("100")),
            ],
        )
    assert "pelo menos 2" in str(exc_info.value)


def test_transaction_decimal_values():
    """Valores decimais funcionam corretamente."""
    t = Transaction(
        date=date(2024, 1, 1),
        description="Compra com centavos",
        postings=[
            Posting(account="expenses:food", amount=Decimal("19.99")),
            Posting(account="assets:bank", amount=Decimal("-19.99")),
        ],
    )
    assert sum(p.amount for p in t.postings) == Decimal("0")


def test_posting_amount_zero_rejected():
    """Posting com amount zero é rejeitado."""
    with pytest.raises(ValidationError):
        Posting(account="assets:bank", amount=Decimal("0"))


def test_posting_empty_account_rejected():
    """Posting com conta vazia é rejeitado."""
    with pytest.raises(ValidationError):
        Posting(account="", amount=Decimal("100"))


def test_transaction_three_postings_balanced():
    """Transação com 3+ postings balanceados é aceita."""
    t = Transaction(
        date=date(2024, 1, 1),
        description="Dividir despesa",
        postings=[
            Posting(account="expenses:food", amount=Decimal("100")),
            Posting(account="assets:bank:alice", amount=Decimal("-60")),
            Posting(account="assets:bank:bob", amount=Decimal("-40")),
        ],
    )
    assert sum(p.amount for p in t.postings) == 0

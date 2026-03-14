"""Testes de integridade contábil (regras de partida dobrada)."""

from datetime import date
from decimal import Decimal

from minha_financa.models import Posting, Transaction


def test_debits_equal_credits():
    """Débitos (positivos) devem igualar créditos (negativos)."""
    debits = Decimal("150.00")
    credits = Decimal("-150.00")
    t = Transaction(
        date=date(2024, 1, 15),
        description="Teste débito=crédito",
        postings=[
            Posting(account="assets:bank", amount=debits),
            Posting(account="income:salary", amount=credits),
        ],
    )
    total_debits = sum(p.amount for p in t.postings if p.amount > 0)
    total_credits = sum(p.amount for p in t.postings if p.amount < 0)
    assert total_debits + total_credits == 0
    assert total_debits == abs(total_credits)


def test_complex_transaction_balance():
    """Transação complexa com múltiplas contas deve balancear."""
    t = Transaction(
        date=date(2024, 2, 1),
        description="Pagamento de conta com split",
        postings=[
            Posting(account="expenses:rent", amount=Decimal("1000")),
            Posting(account="expenses:utilities", amount=Decimal("200")),
            Posting(account="assets:bank", amount=Decimal("-1200")),
        ],
    )
    assert sum(p.amount for p in t.postings) == 0

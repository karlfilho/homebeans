"""Relatórios e agregações contábeis."""

from collections import defaultdict
from decimal import Decimal

from homebeans.models import Transaction


def balance_by_account(transactions: list[Transaction]) -> dict[str, Decimal]:
    """Calcula saldo por conta (débitos - créditos)."""
    balances: dict[str, Decimal] = defaultdict(Decimal)
    for t in transactions:
        for p in t.postings:
            balances[p.account] += p.amount
    return dict(balances)


def balance_report(transactions: list[Transaction]) -> list[tuple[str, Decimal]]:
    """Retorna relatório de saldo ordenado por conta."""
    bal = balance_by_account(transactions)
    return sorted(bal.items(), key=lambda x: x[0])

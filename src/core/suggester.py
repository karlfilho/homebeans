from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from thefuzz import process

from homebeans.models import Posting, Transaction


def _build_description_index(
    transactions: Iterable[Transaction],
) -> dict[str, list[Transaction]]:
    """Indexa transações por descrição normalizada, preservando ordem."""
    index: dict[str, list[Transaction]] = defaultdict(list)
    for t in transactions:
        desc = t.description.strip()
        if not desc:
            continue
        index[desc].append(t)
    return index


def suggest_for_description(
    transactions: list[Transaction],
    description: str,
    threshold: int = 80,
) -> tuple[Posting | None, Decimal | None]:
    """Sugere conta e valor com base em descrições similares.

    Retorna:
        - Posting sugerido (conta + valor) ou None
        - Valor sugerido (Decimal) ou None
    """
    description = description.strip()
    if not description or not transactions:
        return None, None

    index = _build_description_index(transactions)
    choices = list(index.keys())
    if not choices:
        return None, None

    match = process.extractOne(description, choices)
    if not match:
        return None, None

    best_desc, score = match[0], match[1]
    if score < threshold:
        return None, None

    # Usa a última transação com essa descrição como base.
    last_tx = index[best_desc][-1]
    if not last_tx.postings:
        return None, None

    # Heurística simples: usar o último lançamento da transação como default.
    base_posting = last_tx.postings[-1]
    suggested_posting = Posting(account=base_posting.account, amount=base_posting.amount)
    return suggested_posting, suggested_posting.amount


def extract_all_accounts(transactions: Iterable[Transaction]) -> list[str]:
    """Extrai todas as contas distintas do histórico, ordenadas alfabeticamente."""
    accounts_set: set[str] = set()
    for t in transactions:
        for p in t.postings:
            acc = p.account.strip()
            if acc:
                accounts_set.add(acc)
    return sorted(accounts_set)


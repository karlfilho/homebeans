"""Modelos de dados para contabilidade de partida dobrada.

Convenção de sinais:
- Débito: valor positivo
- Crédito: valor negativo
- Soma dos postings sempre zero (débitos = créditos)
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


class Posting(BaseModel):
    """Lançamento individual em uma conta."""

    account: str
    amount: Decimal
    tags: list[str] = Field(default_factory=list)

    @field_validator("account")
    @classmethod
    def account_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Conta não pode ser vazia")
        return v.strip()

    @field_validator("amount")
    @classmethod
    def amount_not_zero(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("Valor do lançamento não pode ser zero")
        return v

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        cleaned = []
        for tag in v:
            tag = tag.strip()
            if tag:
                cleaned.append(tag)
        return cleaned


class Transaction(BaseModel):
    """Transação com múltiplos lançamentos (partida dobrada)."""

    date: date
    description: str
    postings: list[Posting]

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Descrição não pode ser vazia")
        return v.strip()

    @model_validator(mode="after")
    def validate_balanced(self) -> "Transaction":
        """Garante que Débitos + Créditos = 0."""
        if len(self.postings) < 2:
            raise ValueError("Transação deve ter pelo menos 2 lançamentos")
        total = sum(p.amount for p in self.postings)
        if total != Decimal("0"):
            raise ValueError(
                f"Transação desbalanceada: soma = {total} (deve ser 0)"
            )
        return self

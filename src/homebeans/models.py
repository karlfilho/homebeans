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
        v = v.strip()
        if ":" not in v:
            raise ValueError(
                "Conta inválida: use a sintaxe tipo:subconta(:subconta...)"
            )
        parts = [p for p in v.split(":") if p.strip()]
        if len(parts) < 2:
            raise ValueError(
                "Conta inválida: use a sintaxe tipo:subconta(:detalhe...)"
            )
        if len(parts) > 3:
            raise ValueError(
                "Conta inválida: o limite máximo são 3 níveis (tipo:subconta:detalhe). "
                "Se precisar de um 4º nível, transforme-o em uma tag (ex: veiculo:meteor)."
            )
            
        root = parts[0].lower()
        valid_roots = {"ativos", "passivos", "entradas", "despesas", "patrimônio", "patrimonio"}
        if root not in valid_roots:
            raise ValueError(
                f"Raiz da conta inválida ('{root}'). Deve iniciar obrigatoriamente com: ativos, passivos, entradas, despesas ou patrimônio."
            )
            
        # Garante que não existam espaços nos segmentos.
        for seg in parts:
            if any(ch.isspace() for ch in seg):
                raise ValueError(
                    "Conta inválida: não use espaços; separe níveis com ':'"
                )
        return v

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
                if ":" not in tag:
                    raise ValueError(
                        f"Tag inválida ('{tag}'). Tags devem seguir obrigatoriamente a regra chave:valor (ex: veiculo:meteor)"
                    )
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

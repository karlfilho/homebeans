"""Persistência do livro-razão em YAML com Ruamel."""

import uuid
from pathlib import Path

from ruamel.yaml import YAML

from homebeans.models import Transaction


def _transaction_to_dict(t: Transaction) -> dict:
    """Serializa Transaction para dict compatível com YAML.

    O campo `id` é sempre incluído para garantir rastreabilidade.
    """
    return {
        "id": t.id,
        "date": str(t.date),
        "description": t.description,
        "postings": [
            {
                "account": p.account,
                "amount": str(p.amount),
                "tags": p.tags or [],
            }
            for p in t.postings
        ],
    }


def _dict_to_transaction(d: dict) -> Transaction:
    """Desserializa dict para Transaction.

    Migração automática: transações legadas sem campo `id` no YAML
    recebem um UUID gerado na leitura. Na próxima gravação o ID é
    persistido, tornando a migração transparente e permanente.
    """
    # Migração: se o YAML não tiver `id` (transação legada), gera um UUID aqui.
    # Não passamos None para o modelo — o Pydantic ignoraria o default_factory se id=None.
    transaction_id = d.get("id") or str(uuid.uuid4())
    return Transaction(
        id=transaction_id,
        date=d["date"],
        description=d["description"],
        postings=[
            {
                "account": p["account"],
                "amount": p["amount"],
                "tags": p.get("tags", []),
            }
            for p in d["postings"]
        ],
    )


def load_ledger(path: Path) -> list[Transaction]:
    """Carrega transações do arquivo YAML."""
    yaml = YAML()
    yaml.preserve_quotes = True
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = yaml.load(f)
    if data is None:
        return []
    raw = data.get("transactions", [])
    return [_dict_to_transaction(t) for t in raw]


def save_ledger(path: Path, transactions: list[Transaction]) -> None:
    """Salva transações no arquivo YAML preservando comentários."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=2, offset=0)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "transactions": [_transaction_to_dict(t) for t in transactions],
    }
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f)

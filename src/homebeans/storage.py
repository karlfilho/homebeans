"""Persistência do livro-razão em YAML com Ruamel."""

import shutil
import uuid
from pathlib import Path

from ruamel.yaml import YAML

from homebeans.models import Transaction

# Número de backups automáticos mantidos ao lado do ledger.
_MAX_BACKUPS = 3


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


def _rotate_backups(path: Path) -> None:
    """Rotaciona backups do ledger antes de cada gravação.

    Mantém até _MAX_BACKUPS arquivos .bak.<N> ao lado do ledger:
      ledger.yaml.bak.1  ← backup mais recente
      ledger.yaml.bak.2
      ledger.yaml.bak.3  ← backup mais antigo (descartado na próxima rotação)

    Se o arquivo ainda não existir, não faz nada.
    """
    if not path.exists():
        return
    # Desloca os backups existentes: .bak.2 → .bak.3, .bak.1 → .bak.2
    for i in range(_MAX_BACKUPS - 1, 0, -1):
        src = path.with_suffix(f".yaml.bak.{i}")
        dst = path.with_suffix(f".yaml.bak.{i + 1}")
        if src.exists():
            shutil.copy2(src, dst)
    # Copia o arquivo atual para .bak.1
    shutil.copy2(path, path.with_suffix(".yaml.bak.1"))


def save_ledger(path: Path, transactions: list[Transaction]) -> None:
    """Salva transações no arquivo YAML de forma atômica.

    Fluxo seguro:
      1. Rotaciona backups do arquivo atual (.bak.1 / .bak.2 / .bak.3)
      2. Serializa para um arquivo temporário (.tmp) no mesmo diretório
      3. Renomeia o .tmp sobre o destino final (operação atômica no SO)

    Dessa forma, uma interrupção durante a escrita nunca corrompe o
    ledger — o arquivo anterior permanece intacto nos backups.
    """
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=2, offset=0)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "transactions": [_transaction_to_dict(t) for t in transactions],
    }

    # Faz backup do arquivo atual antes de sobrescrever
    _rotate_backups(path)

    # Escreve em arquivo temporário no mesmo diretório (garante mesmo volume
    # para que o rename seja atômico no nível do sistema de arquivos)
    tmp_path = path.with_suffix(".yaml.tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f)
        # Rename atômico: substitui o destino somente após escrita completa
        tmp_path.replace(path)
    except Exception:
        # Se falhou, remove o .tmp para não deixar lixo
        if tmp_path.exists():
            tmp_path.unlink()
        raise

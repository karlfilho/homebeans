"""Configurações globais do HomeBeans."""

import os
from pathlib import Path


def get_ledger_path() -> Path:
    path = os.getenv("LEDGER_PATH", "./data/ledger.yaml")
    return Path(path)

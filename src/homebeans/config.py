"""Configurações globais do HomeBeans."""

import os
from pathlib import Path


def get_ledger_path() -> Path:
    from homebeans.demo_mode import get_demo_ledger_path, is_demo_active

    if is_demo_active():
        return get_demo_ledger_path()
    path = os.getenv("LEDGER_PATH", "./data/ledger.yaml")
    return Path(path)

"""Gerenciamento do modo de demonstração do HomeBeans.

O modo demo redireciona todas as operações de leitura e escrita para um
ledger fictício separado, mantendo o ledger real intocado.
"""

import shutil
from pathlib import Path

# Estado em memória — válido enquanto o servidor MCP estiver rodando
_demo_active: bool = False

# Caminhos relativos ao diretório de trabalho do processo
_DEMO_TEMPLATE_PATH = Path("./data/demo_ledger_template.yaml")
_DEMO_WORKING_PATH = Path("./data/demo_ledger.yaml")


def is_demo_active() -> bool:
    """Retorna True se o modo de demonstração está ativo."""
    return _demo_active


def get_demo_ledger_path() -> Path:
    """Retorna o caminho do ledger de trabalho da demonstração."""
    return _DEMO_WORKING_PATH


def enter_demo() -> str:
    """Ativa o modo demo.

    Copia o template de demonstração para um arquivo de trabalho e
    redireciona get_ledger_path() para esse arquivo.

    Retorna "ok" em caso de sucesso ou uma mensagem de erro.
    """
    global _demo_active

    if _demo_active:
        return "Modo de demonstração já está ativo."

    if not _DEMO_TEMPLATE_PATH.exists():
        return (
            f"Erro: template de demonstração não encontrado em '{_DEMO_TEMPLATE_PATH}'. "
            "Verifique se o arquivo 'data/demo_ledger_template.yaml' existe."
        )

    _DEMO_WORKING_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_DEMO_TEMPLATE_PATH, _DEMO_WORKING_PATH)
    _demo_active = True
    return "ok"


def exit_demo() -> str:
    """Desativa o modo demo e descarta o ledger de trabalho.

    Remove o arquivo de trabalho e restaura o redirecionamento para o
    ledger real definido em LEDGER_PATH (ou o padrão).

    Retorna "ok" em caso de sucesso ou uma mensagem de erro.
    """
    global _demo_active

    if not _demo_active:
        return "Modo de demonstração não está ativo."

    if _DEMO_WORKING_PATH.exists():
        _DEMO_WORKING_PATH.unlink()

    _demo_active = False
    return "ok"

## Estrutura do projeto

- **src/homebeans**
  - `__init__.py`: inicialização do pacote.
  - `config.py`: resolução do caminho do ledger ativo via `get_ledger_path()` — consulta `demo_mode.is_demo_active()` para redirecionar automaticamente para o ledger de demo quando necessário.
  - `models.py`: modelos Pydantic (`Posting`, `Transaction`) e validações de partida dobrada (soma zero, prefixos de conta, máximo 3 níveis, formato de tags).
  - `storage.py`: leitura e escrita do livro-razão YAML com Ruamel.YAML (preserva comentários).
  - `mcp_server.py`: servidor FastMCP com todas as tools e prompts MCP. Tools disponíveis:
    - Leitura: `get_balance`, `get_transactions`, `get_recent_transactions`, `get_accounts_tree`, `get_tags_list`
    - Estatísticas: `get_ledger_stats`, `get_account_statement`, `get_spending_summary`
    - Relatórios: `get_income_statement`, `get_balance_sheet`, `get_cashflow`
    - Escrita: `add_transaction`, `edit_transaction`, `delete_transaction`, `clear_journal`
    - Demo: `enter_demo_mode`, `exit_demo_mode`, `start_demo_tutorial`
    - Prompt: `homebeans_guide`
  - `cli.py`: interface de linha de comando (Typer) com comandos `add`, `balance`, `report`, `accounts`, `journal-clear`, `mcp`.
  - `reports.py`: geração de todos os relatórios locais (balanço por conta, DRE, balanço patrimonial, fluxo de caixa, extrato de conta, resumo de gastos, estatísticas do ledger, árvore ASCII).
  - `demo_mode.py`: gerenciamento do modo demo em memória. Estado `_demo_active` controla o redirecionamento; `enter_demo()` copia o template para um arquivo de trabalho; `exit_demo()` descarta o arquivo de trabalho.

- **src/core**
  - `suggester.py`: motor de sugestões para o wizard `hb add`, usando fuzzy matching (`thefuzz`) e histórico do livro-razão para sugerir conta e valor, além de extrair lista de contas para autocomplete.

- **data**
  - `ledger.yaml`: ledger real do usuário (caminho configurável via env `LEDGER_PATH`).
  - `demo_ledger_template.yaml`: template imutável com 48 transações fictícias cobrindo Jan–Mar 2026, usado como fonte do modo demo.
  - `demo_ledger.yaml`: arquivo de trabalho do modo demo (criado ao entrar no demo, descartado ao sair).

- **tests**
  - `test_models.py`: testes dos modelos Pydantic e validações.
  - `test_integrity.py`: testes de integridade geral do sistema.
  - `test_demo_mode.py`: 14 testes cobrindo ativação/desativação do demo, isolamento do ledger real, integridade do template e integração com `config.get_ledger_path()`.

## Estrutura do projeto

### `src/homebeans/`

- **`models.py`** — modelos Pydantic (`Posting`, `Transaction`) e todas as validações:
  - Partida dobrada (soma zero obrigatória)
  - Nomenclatura de contas (5 raízes válidas, máximo 3 níveis)
  - Formato de tags (`chave:valor`)
  - UUID gerado automaticamente em cada transação

- **`storage.py`** — leitura e escrita do `ledger.yaml` via Ruamel.YAML:
  - Preserva comentários no arquivo
  - Migração automática: transações sem `id` recebem UUID na primeira leitura

- **`mcp_server.py`** — servidor FastMCP com 15 ferramentas e 1 prompt:
  - Ferramentas de consulta: `get_balance`, `get_transactions`, `get_recent_transactions`, `get_accounts_tree`, `get_tags_list`
  - Ferramentas estatísticas (cálculo 100% local): `get_ledger_stats`, `get_account_statement`, `get_spending_summary`
  - Relatórios periódicos: `get_income_statement`, `get_balance_sheet`, `get_cashflow`
  - Ferramentas de escrita: `add_transaction`, `edit_transaction`, `delete_transaction`, `clear_journal`
  - Prompt `homebeans_guide`: guia completo para o assistente — regras, mapa intenção→ferramenta, fluxo recomendado

- **`reports.py`** — toda a lógica de relatórios e estatísticas:
  - `balance_report` — saldos agrupados por conta
  - `generate_income_statement` — DRE por período
  - `generate_balance_sheet` — balanço patrimonial acumulativo
  - `generate_cashflow` — variação líquida de ativos
  - `generate_account_statement` — extrato com saldo acumulado linha a linha
  - `generate_spending_summary` — top N categorias de despesa com percentual
  - `generate_ledger_stats` — estatísticas gerais do ledger
  - `filter_by_dates`, `group_by_period`, `balance_by_account` — helpers reutilizáveis

- **`cli.py`** — interface Typer com comandos:
  - `add` — wizard interativo com autocomplete e sugestões por fuzzy matching
  - `balance` — tabela de saldos
  - `report` — últimas N transações
  - `accounts` — lista e árvore de contas
  - `mcp` — inicia o servidor MCP via stdio

- **`suggester.py`** — motor de sugestões para o wizard `add`:
  - Fuzzy matching (`thefuzz`) para sugerir conta e valor com base em descrições similares
  - Extração de lista de contas do histórico para autocomplete

- **`config.py`** — leitura de configuração via variáveis de ambiente (`LEDGER_PATH`)

### `src/core/`

- **`suggester.py`** — alias/re-exportação de `src/homebeans/suggester.py`

### `tests/`

- **`test_models.py`** — validação dos modelos Pydantic e regras de negócio
- **`test_integrity.py`** — integridade da partida dobrada no ledger real
- **`test_transaction_id.py`** — UUID nas transações, migração, delete/edit por ID
- **`test_report_filters.py`** — filtros de data nos relatórios periódicos e `get_balance`
- **`test_statistical_tools.py`** — `get_ledger_stats`, `get_account_statement`, `get_spending_summary`

### Arquivos de configuração

- **`data/ledger.yaml`** — ledger principal (configurável via `LEDGER_PATH`)
- **`.env.example`** — template de variáveis de ambiente
- **`pyproject.toml`** — dependências e configuração do projeto (UV)

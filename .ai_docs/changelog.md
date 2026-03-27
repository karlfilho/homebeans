## Changelog

---

### [2026-03-26] Ferramentas estatísticas com cálculo local

- **`get_ledger_stats()`** — visão geral do ledger em uma chamada: total de transações, período coberto, contas e tags distintas, média de transações por mês. Ideal como contexto no início de uma conversa.
- **`get_account_statement(account, start_date?, end_date?)`** — extrato estilo bancário com saldo acumulado linha a linha. Aceita filtro parcial de conta e intervalo de datas.
- **`get_spending_summary(period?, start_date?, end_date?, top_n?)`** — top N categorias de despesa (`despesas:<subcategoria>`) com valor e percentual do total. Suporta agrupamento por período e filtro de datas.
- Toda a lógica reside em `reports.py`; as ferramentas em `mcp_server.py` apenas carregam o ledger e delegam.
- 21 novos testes em `tests/test_statistical_tools.py`.

---

### [2026-03-26] Filtros de data nos relatórios e filtro de conta no saldo

- `get_income_statement`, `get_balance_sheet` e `get_cashflow` passaram a aceitar `start_date` e `end_date` (formato `YYYY-MM-DD`).
- `get_balance` ganhou parâmetro `account_filter` opcional para filtrar por prefixo de conta.
- Helper `_parse_report_dates` centraliza a conversão e validação de strings de data.
- Novos testes em `tests/test_report_filters.py`.

---

### [2026-03-26] `get_recent_transactions` com filtros

- Nova ferramenta `get_recent_transactions(limit, account_filter?, tag_filter?)` — retorna as últimas N transações com interface simplificada.
- Suporta filtro por conta (prefixo parcial) e por tag.
- Complementa `get_transactions` para casos de uso diretos como "quais as últimas 10 transações da conta banco?".

---

### [2026-03-26] UUID em todas as transações

- Campo `id` (UUID v4) adicionado ao modelo `Transaction`, gerado automaticamente na criação.
- Migração automática: transações no YAML sem `id` recebem um UUID na primeira leitura, sem perda de dados.
- `add_transaction` retorna o ID gerado na resposta.
- `get_transactions` e `get_recent_transactions` exibem o ID de cada transação.
- `delete_transaction` e `edit_transaction` aceitam `transaction_id` como parâmetro prioritário (mais preciso); `date + description` continua funcionando como fallback.
- Novos testes em `tests/test_transaction_id.py`.

---

### [2026-03-20] Remoção de relatórios HTML/Plotly

- Removidos `viz.py` e dependência `plotly` — funcionalidade tornou-se obsoleta com a integração MCP.
- Removida ferramenta `generate_html_report` do servidor MCP.
- Removido comando `chart` da CLI.

---

### [2026-03-15] Wizard interativo no `add` com sugestões

- Adicionado `src/homebeans/suggester.py` (anteriormente `src/core/suggester.py`) para sugerir conta e valor com fuzzy matching (`thefuzz`) e histórico do ledger.
- Refatorado comando `add` em `cli.py` para wizard interativo via Questionary:
  - Autocomplete de contas a partir do histórico
  - Sugestão automática de conta/valor para descrições similares
  - Validação em tempo real via Pydantic (`Posting`, `Transaction`)
  - Loop de postings até saldo zerar, com exibição do quanto falta a cada etapa

---

### [2026-03-15] Comandos de journal e contas + validação de sintaxe

- `homebeans accounts` — lista e árvore (`--tree`) das contas em uso, com filtros por tipo.
- `homebeans journal-clear` (equivalente ao MCP `clear_journal`) — limpa o journal com confirmação.
- Validação reforçada em `Posting.account`: exige hierarquia por `:`, sem espaços, máximo 3 níveis.

---

### [2026-03-10] Relatórios avançados e servidor MCP

- Servidor FastMCP (`mcp_server.py`) com ferramentas iniciais: `get_balance`, `get_transactions`, `add_transaction`, `delete_transaction`, `edit_transaction`, `get_accounts_tree`, `get_tags_list`, `get_income_statement`, `get_balance_sheet`, `get_cashflow`.
- `reports.py` com DRE, Balanço Patrimonial e Fluxo de Caixa com agrupamento por período.
- Árvore ASCII de contas via `format_ascii_tree`.
- Prompt `homebeans_guide` embutido no servidor para orientar o assistente.

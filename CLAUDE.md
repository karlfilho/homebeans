# HomeBeans — CLAUDE.md

Sistema de contabilidade de partida dobrada em Python, inspirado no hledger. Persiste dados em YAML e expõe funcionalidades via servidor MCP (Claude Desktop) e CLI (Typer).

## Stack

- **Python 3.11+**, gerenciado com **UV**
- **Pydantic V2** — validação e modelagem de domínio
- **Ruamel.YAML** — serialização (preserva comentários)
- **FastMCP** — servidor MCP via stdio
- **Typer + Rich** — CLI interativa
- **Questionary** — wizard interativo no CLI
- **thefuzz** — fuzzy matching para sugestões de contas

## Estrutura do projeto

```
src/homebeans/
├── config.py       # Resolução do caminho do ledger ativo (real ou demo)
├── models.py       # Pydantic: Posting, Transaction + todas as validações
├── storage.py      # Leitura/escrita do ledger.yaml (Ruamel.YAML)
├── mcp_server.py   # Servidor FastMCP com 18 tools + 1 prompt
├── cli.py          # Comandos Typer: add, balance, report, accounts, journal-clear, mcp
├── reports.py      # DRE, Balanço Patrimonial, Fluxo de Caixa, extrato, estatísticas
└── demo_mode.py    # Gerenciamento do modo demonstração em memória

src/core/
└── suggester.py    # Sugestões por fuzzy matching + extração de contas do histórico

tests/
├── test_models.py              # Validação dos modelos Pydantic
├── test_integrity.py           # Integridade da partida dobrada
├── test_demo_mode.py           # Ativação/desativação e isolamento do modo demo
├── test_statistical_tools.py   # Ferramentas get_ledger_stats, get_account_statement, etc.
├── test_get_balance.py         # Ferramenta get_balance
├── test_get_recent_transactions.py
├── test_report_date_filters.py # Filtros de data nos relatórios
└── test_transaction_id.py      # Persistência de UUID nas transações
```

## Dados

- Arquivo: `./data/ledger.yaml` (configurável via env `LEDGER_PATH`)
- Formato:

```yaml
transactions:
  - date: "2026-03-15"
    description: "Compra no mercado"
    postings:
      - account: "despesas:alimentacao:mercado"
        amount: "125.50"
        tags: ["local:carrefour"]
      - account: "ativos:carteira"
        amount: "-125.50"
        tags: []
```

## Regras de negócio críticas

### Partida dobrada
- Toda transação deve ter ≥ 2 postings
- A soma de todos os `amount` deve ser **exatamente zero**
- Positivo = Débito | Negativo = Crédito

### Nomenclatura de contas — OBRIGATÓRIO
- Somente 5 raízes válidas: `ativos`, `passivos`, `entradas`, `despesas`, `patrimônio` (aceita `patrimonio` sem acento)
- Formato: `raiz:subconta` ou `raiz:subconta:detalhe`
- **Máximo 3 níveis** — 4º nível é estritamente proibido
- Se precisar de mais detalhe, use uma tag (ex.: `veiculo:meteor`)
- Sem espaços nos segmentos; use `:` para hierarquia

### Tags — OBRIGATÓRIO
- Formato obrigatório: `chave:valor` (ex.: `veiculo:meteor`, `viagem:sp`)
- Tags vazias são permitidas (lista vazia `[]`)
- **Priorizar reuso** de tags existentes antes de criar novas

### Convenção de sinais
| Tipo de conta | Débito (positivo) | Crédito (negativo) |
|---|---|---|
| Ativos | Aumenta | Diminui |
| Despesas | Aumenta | Diminui |
| Entradas | Diminui | Aumenta |
| Passivos | Diminui | Aumenta |
| Patrimônio | Diminui | Aumenta |

## MCP Tools disponíveis

| Tool | Descrição |
|---|---|
| `get_balance(account_filter?)` | Saldo atual agrupado por conta |
| `get_transactions(limit, start_date, end_date, account_filter, description_filter, tag_filter)` | Consulta com filtros avançados |
| `get_recent_transactions(limit, account_filter?, tag_filter?)` | Últimas N transações |
| `get_ledger_stats()` | Estatísticas gerais: total de transações, período, contas e tags distintas |
| `get_account_statement(account, start_date?, end_date?)` | Extrato com saldo acumulado linha a linha |
| `get_spending_summary(period, start_date?, end_date?, top_n)` | Maiores gastos por categoria com percentuais |
| `add_transaction(date_str, description, postings)` | Adiciona transação validada |
| `edit_transaction(transaction_id?, date_str?, description?, new_date_str?, new_description?, new_postings?)` | Edição parcial — localiza por ID (preferido) ou data+descrição |
| `delete_transaction(transaction_id?, date_str?, description?)` | Remove — localiza por ID (preferido) ou data+descrição |
| `get_accounts_tree()` | Árvore ASCII de todas as contas em uso |
| `get_tags_list()` | Lista única de todas as tags em uso |
| `get_income_statement(period, start_date?, end_date?)` | DRE: entradas vs despesas por período |
| `get_balance_sheet(period, start_date?, end_date?)` | Balanço patrimonial acumulativo |
| `get_cashflow(period, start_date?, end_date?)` | Variação líquida de ativos por período |
| `clear_journal(confirmation)` | Apaga tudo — requer `"CONFIRMO_LIMPEZA_TOTAL"` |
| `enter_demo_mode()` | Ativa modo demo: redireciona para ledger fictício pré-carregado |
| `exit_demo_mode()` | Encerra modo demo e descarta o ledger fictício |
| `start_demo_tutorial()` | Retorna roteiro completo para tutorial guiado no modo demo |

Parâmetro `period` aceita: `"day"`, `"week"`, `"month"`, `"year"`, `"all"` (padrão: `"month"`).

## CLI

```bash
uv run homebeans add             # wizard interativo
uv run homebeans balance         # tabela de saldos
uv run homebeans report          # últimas 20 transações
uv run homebeans accounts --tree # árvore de contas
uv run homebeans mcp             # inicia servidor MCP via stdio
```

## Desenvolvimento

```bash
uv sync          # instalar dependências
uv run pytest tests/ -v  # rodar testes
```

Copie `.env.example` para `.env` se quiser customizar `LEDGER_PATH`.

## Docs internas

- `.ai_docs/structure.md` — estrutura do projeto
- `.ai_docs/changelog.md` — histórico de features

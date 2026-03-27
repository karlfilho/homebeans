# HomeBeans

Sistema de contabilidade de partida dobrada em Python, inspirado no [hledger](https://hledger.org/).
Persiste dados em YAML e expõe funcionalidades via servidor MCP (Claude Desktop) e CLI (Typer).

## Características

- **Partida dobrada** — validação rigorosa: soma dos postings deve ser sempre zero
- **Persistência em YAML** — formato legível, preserva comentários (Ruamel.YAML)
- **Servidor MCP** — 15 ferramentas para uso com Claude Desktop ou qualquer cliente MCP
- **CLI moderna** — Typer + Rich com wizard interativo e tabelas coloridas
- **Cálculo 100% local** — todas as estatísticas e relatórios são computados em Python
- **IDs únicos** — cada transação recebe um UUID para edição e remoção precisas

## Pré-requisitos

- Python 3.11+
- [UV](https://docs.astral.sh/uv/)

## Instalação

```bash
git clone https://github.com/karlfilho/homebeans.git
cd homebeans
uv sync
cp .env.example .env   # ajuste LEDGER_PATH se necessário
```

## Uso via Claude Desktop (MCP)

Adicione ao seu `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "homebeans": {
      "command": "uv",
      "args": ["run", "--directory", "/caminho/para/homebeans", "homebeans", "mcp"]
    }
  }
}
```

Reinicie o Claude Desktop. Todas as 15 ferramentas estarão disponíveis.

## Uso via CLI

```bash
uv run homebeans add             # wizard interativo para nova transação
uv run homebeans balance         # tabela de saldos por conta
uv run homebeans report          # últimas 20 transações
uv run homebeans accounts --tree # árvore hierárquica de contas
uv run homebeans mcp             # inicia o servidor MCP via stdio
```

## Ferramentas MCP

### Consulta

| Ferramenta | Descrição |
|---|---|
| `get_balance(account_filter?)` | Saldos agrupados por conta |
| `get_transactions(...)` | Consulta com filtros de data, conta, descrição e tag |
| `get_recent_transactions(limit, account_filter?, tag_filter?)` | Últimas N transações |
| `get_accounts_tree()` | Árvore ASCII das contas em uso |
| `get_tags_list()` | Lista de todas as tags em uso |

### Estatísticas (cálculo local)

| Ferramenta | Descrição |
|---|---|
| `get_ledger_stats()` | Visão geral: total, período, contas, tags, média/mês |
| `get_account_statement(account, start_date?, end_date?)` | Extrato com saldo acumulado |
| `get_spending_summary(period?, start_date?, end_date?, top_n?)` | Top N categorias de despesa com % |

### Relatórios periódicos

| Ferramenta | Descrição |
|---|---|
| `get_income_statement(period?, start_date?, end_date?)` | DRE: entradas vs despesas |
| `get_balance_sheet(period?, start_date?, end_date?)` | Balanço patrimonial |
| `get_cashflow(period?, start_date?, end_date?)` | Variação líquida de ativos |

### Escrita

| Ferramenta | Descrição |
|---|---|
| `add_transaction(date_str, description, postings)` | Adiciona transação validada |
| `edit_transaction(...)` | Edição parcial por ID ou data+descrição |
| `delete_transaction(...)` | Remoção por ID ou data+descrição |
| `clear_journal(confirmation)` | Apaga tudo — requer `"CONFIRMO_LIMPEZA_TOTAL"` |

> Parâmetro `period` aceita: `day`, `week`, `month`, `year`, `all` (padrão: `month`).

## Formato do ledger

```yaml
transactions:
  - id: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    date: "2026-03-15"
    description: "Compra no mercado"
    postings:
      - account: "despesas:alimentacao:mercado"
        amount: "125.50"
        tags: ["local:carrefour"]
      - account: "ativos:carteira"
        amount: "-125.50"
        tags: []
```

## Regras de negócio

- **Partida dobrada**: soma de todos os `amount` deve ser exatamente zero
- **Contas**: 5 raízes válidas — `ativos`, `passivos`, `entradas`, `despesas`, `patrimônio`
- **Níveis**: máximo 3 (`despesas:moradia:aluguel`); use tags para mais detalhe
- **Tags**: formato `chave:valor` obrigatório (`local:carrefour`, `viagem:sp`)

## Estrutura do projeto

```
src/homebeans/
├── models.py       # Pydantic: Posting, Transaction + validações
├── storage.py      # Leitura/escrita do ledger.yaml (Ruamel.YAML)
├── mcp_server.py   # Servidor FastMCP com 15 tools + 1 prompt
├── cli.py          # Comandos Typer: add, balance, report, accounts, mcp
├── reports.py      # DRE, Balanço, Fluxo de Caixa, estatísticas, extrato
└── suggester.py    # Fuzzy matching para sugestões no wizard CLI

src/core/
└── suggester.py    # (alias — ver src/homebeans/suggester.py)

tests/
├── test_models.py           # Validação dos modelos Pydantic
├── test_integrity.py        # Integridade da partida dobrada
├── test_transaction_id.py   # UUID e migração
├── test_statistical_tools.py # get_ledger_stats, get_account_statement, get_spending_summary
└── test_report_filters.py   # Filtros de data nos relatórios
```

## Testes

```bash
uv run pytest tests/ -v
```

## Licença

MIT

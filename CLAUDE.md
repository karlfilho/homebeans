# HomeBeans — CLAUDE.md

Sistema de contabilidade de partida dobrada em Python, inspirado no hledger. Persiste dados em YAML e expõe funcionalidades via servidor MCP (Claude Desktop) e CLI (Typer).

## Stack

- **Python 3.11+**, gerenciado com **UV**
- **Pydantic V2** — validação e modelagem de domínio
- **Ruamel.YAML** — serialização (preserva comentários)
- **FastMCP** — servidor MCP via stdio
- **Typer + Rich** — CLI interativa
- **Plotly** — exportação de gráficos HTML
- **Questionary** — wizard interativo no CLI
- **thefuzz** — fuzzy matching para sugestões de contas

## Estrutura do projeto

```
src/homebeans/
├── models.py       # Pydantic: Posting, Transaction + todas as validações
├── storage.py      # Leitura/escrita do ledger.yaml (Ruamel.YAML)
├── mcp_server.py   # Servidor FastMCP com 12 tools + 1 prompt
├── cli.py          # Comandos Typer: add, balance, report, chart, accounts, journal-clear, mcp
├── reports.py      # DRE, Balanço Patrimonial, Fluxo de Caixa, árvore ASCII
└── viz.py          # Gráfico de barras Plotly exportado em HTML

src/core/
└── suggester.py    # Sugestões por fuzzy matching + extração de contas do histórico

tests/
├── test_models.py      # Validação dos modelos Pydantic
└── test_integrity.py   # Integridade da partida dobrada
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
| `get_balance()` | Saldo atual agrupado por conta |
| `get_transactions(limit, start_date, end_date, account_filter, description_filter, tag_filter)` | Consulta com filtros avançados |
| `add_transaction(date_str, description, postings)` | Adiciona transação validada |
| `edit_transaction(date_str, description, new_date_str?, new_description?, new_postings?)` | Edição parcial de transação |
| `delete_transaction(date_str, description)` | Remove transação por data + descrição |
| `get_accounts_tree()` | Árvore ASCII de todas as contas em uso |
| `get_tags_list()` | Lista única de todas as tags em uso |
| `get_income_statement(period)` | DRE: entradas vs despesas por período |
| `get_balance_sheet(period)` | Balanço patrimonial acumulativo |
| `get_cashflow(period)` | Variação líquida de ativos por período |
| `generate_html_report(output_filename)` | Exporta gráfico Plotly em HTML |
| `clear_journal(confirmation)` | Apaga tudo — requer `"CONFIRMO_LIMPEZA_TOTAL"` |

Parâmetro `period` aceita: `"day"`, `"week"`, `"month"`, `"year"`, `"all"` (padrão: `"month"`).

## CLI

```bash
uv run homebeans add             # wizard interativo
uv run homebeans balance         # tabela de saldos
uv run homebeans report          # últimas 20 transações
uv run homebeans accounts --tree # árvore de contas
uv run homebeans chart           # gráfico HTML
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

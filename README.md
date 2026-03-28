# HomeBeans

Sistema de contabilidade de **partida dobrada** em Python, inspirado no [hledger](https://hledger.org/). Persiste dados em YAML simples e se integra com qualquer assistente de IA que suporte o protocolo **MCP** — Claude, GPT, Gemini, e outros.

> **Novo no controle financeiro?** Veja a seção [Como funciona a partida dobrada](#como-funciona-a-partida-dobrada) antes de começar.

---

## Características

- **Partida dobrada**: cada centavo tem origem e destino — o sistema valida isso automaticamente
- **Dados em YAML**: arquivo de texto simples, legível, fácil de versionar e fazer backup
- **Integração com IA via MCP**: converse com seu assistente favorito para registrar gastos, consultar saldos e gerar relatórios
- **CLI interativa**: wizard guiado para adicionar transações sem digitar nenhum comando complexo
- **Modo demonstração**: explore sem risco — dados fictícios, ledger real intocado
- **Tutorial guiado**: a IA pode conduzir um tutorial prático direto no modo demo

---

## Pré-requisitos

- Python 3.11+
- [UV](https://docs.astral.sh/uv/) — gerenciador de dependências moderno para Python

**Instalar o UV** (caso não tenha):
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## Instalação

```bash
git clone https://github.com/karlfilho/homebeans.git
cd homebeans
uv sync
```

Crie seu arquivo de configuração (opcional):
```bash
cp .env.example .env
# Edite .env se quiser salvar o ledger em outro caminho
```

---

## Como funciona a partida dobrada

Partida dobrada é uma regra simples: **todo dinheiro que sai de algum lugar chega em algum lugar**. Cada transação tem pelo menos dois lançamentos cuja soma é sempre zero.

**Exemplo:** você comprou um café por R$ 10,00 em dinheiro.
- O dinheiro **saiu** da sua carteira → `ativos:carteira: -10.00`
- O gasto **entrou** em despesas → `despesas:alimentacao:cafe: +10.00`
- Soma: `-10 + 10 = 0` ✓

O HomeBeans usa 5 tipos de conta:

| Tipo | Para quê | Exemplos |
|------|----------|---------|
| `ativos` | O que você possui | carteira, banco, investimentos |
| `passivos` | O que você deve | cartão de crédito, empréstimos |
| `entradas` | De onde vem dinheiro | salário, freelance, aluguel recebido |
| `despesas` | Para onde vai dinheiro | alimentação, moradia, transporte |
| `patrimônio` | Capital inicial | saldo inicial das contas |

Contas usam hierarquia com `:` e aceitam até 3 níveis:
```
despesas:alimentacao:mercado   ✓  (3 níveis — OK)
ativos:banco                   ✓  (2 níveis — OK)
despesas:a:b:c                 ✗  (4 níveis — proibido, use uma tag)
```

Para detalhes extras, use **tags** no formato `chave:valor`:
```
tag: veiculo:gol
tag: viagem:sp
tag: fornecedor:claro
```

---

## Usando a CLI

### Adicionar uma transação (wizard interativo)

```bash
uv run homebeans add
```

O wizard fará perguntas passo a passo: data, descrição, contas e valores. Ele sugere automaticamente contas já usadas no histórico e valida se os lançamentos somam zero antes de salvar.

### Ver saldo das contas

```bash
uv run homebeans balance
```

### Ver transações recentes

```bash
uv run homebeans report
```

### Ver árvore de contas

```bash
uv run homebeans accounts --tree
```

---

## Usando com um assistente de IA (via MCP)

O HomeBeans funciona como um **servidor MCP** — um protocolo aberto que permite que assistentes de IA usem ferramentas externas. Funciona com qualquer cliente que suporte MCP (Claude Desktop, Cursor, Zed, Continue, etc.).

### Iniciar o servidor MCP

```bash
uv run homebeans mcp
```

### Configurar no Claude Desktop

Edite o arquivo de configuração do Claude Desktop:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

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

Reinicie o Claude Desktop. A partir daí, você pode conversar naturalmente:

> *"Registra um almoço de R$ 45 que paguei com cartão de débito hoje"*
> *"Qual foi meu gasto total com alimentação este mês?"*
> *"Mostre o fluxo de caixa dos últimos 3 meses"*

### Ferramentas disponíveis via MCP

| Ferramenta | O que faz |
|-----------|-----------|
| `get_balance` | Saldo atual de todas as contas |
| `get_transactions` | Consulta com filtros de data, conta, tag e descrição |
| `get_recent_transactions` | Últimas N transações |
| `get_accounts_tree` | Árvore hierárquica de contas em uso |
| `get_tags_list` | Todas as tags em uso |
| `get_ledger_stats` | Estatísticas gerais do ledger |
| `get_account_statement` | Extrato detalhado de uma conta com saldo acumulado |
| `get_spending_summary` | Maiores gastos por categoria com percentuais |
| `get_income_statement` | DRE: entradas vs despesas por período |
| `get_balance_sheet` | Balanço patrimonial acumulativo |
| `get_cashflow` | Variação líquida de ativos por período |
| `add_transaction` | Registra nova transação validada |
| `edit_transaction` | Edita transação existente |
| `delete_transaction` | Remove transação |
| `clear_journal` | Apaga tudo (requer confirmação explícita) |
| `enter_demo_mode` | Ativa modo demo com dados fictícios |
| `exit_demo_mode` | Encerra modo demo |
| `start_demo_tutorial` | Inicia tutorial guiado no modo demo |

O parâmetro `period` dos relatórios aceita: `"day"`, `"week"`, `"month"`, `"year"`, `"all"`.

---

## Modo Demonstração

Quer explorar o HomeBeans sem mexer nos seus dados reais? Peça ao assistente para ativar o modo demo:

> *"Ativa o modo demonstração"*

O assistente vai perguntar se você quer um tutorial guiado. O tutorial explica a partida dobrada e propõe 3 exercícios práticos usando dados fictícios pré-carregados. Seu ledger pessoal permanece intocado durante toda a demonstração.

Para encerrar:
> *"Sai do modo demo"*

---

## Estrutura do projeto

```
src/homebeans/
├── config.py       # Resolução do caminho do ledger ativo (real ou demo)
├── models.py       # Pydantic: Posting, Transaction + todas as validações
├── storage.py      # Leitura/escrita do ledger.yaml (Ruamel.YAML)
├── mcp_server.py   # Servidor FastMCP com 18 tools + 1 prompt
├── cli.py          # Comandos Typer: add, balance, report, accounts, journal-clear, mcp
├── reports.py      # DRE, Balanço Patrimonial, Fluxo de Caixa, extrato, estatísticas
└── demo_mode.py    # Gerenciamento do modo demonstração

src/core/
└── suggester.py    # Sugestões por fuzzy matching + extração de contas do histórico

data/
├── ledger.yaml                  # Seu ledger (ignorado pelo git — seus dados ficam locais)
└── demo_ledger_template.yaml    # Dados fictícios para o modo demo
```

---

## Seus dados ficam no seu computador

O arquivo `data/ledger.yaml` está listado no `.gitignore` — ele **nunca sobe para o GitHub**. Seus dados financeiros ficam exclusivamente na sua máquina.

---

## Testes

```bash
uv run pytest tests/ -v
```

91 testes cobrindo modelos, partida dobrada, modo demo, ferramentas MCP e relatórios.

---

## Licença

MIT

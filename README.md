# HomeBeans

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-cli%20%2B%20mcp-4b5563)](#usando-com-um-assistente-de-ia-via-mcp)
[![Tests](https://img.shields.io/badge/tests-91%20passing-success)](#testes)

Sistema de contabilidade de **partida dobrada** em Python, inspirado no [hledger](https://hledger.org/). Persiste dados em YAML simples e se integra com assistentes de IA via **MCP**.

> Use pela CLI ou conecte ao Claude, GPT, Gemini, Cursor, Zed e outros clientes compatíveis com MCP.

## Visão geral

HomeBeans foi feito para quem quer controlar finanças pessoais com uma base mais confiável do que planilhas soltas, sem abrir mão de arquivos simples e legíveis.

Ele combina:
- **Partida dobrada**, com validação automática de lançamentos.
- **YAML local**, fácil de ler, versionar e fazer backup.
- **CLI interativa**, para registrar transações sem decorar comandos complexos.
- **Servidor MCP**, para usar o ledger com assistentes de IA.
- **Modo demo**, para explorar tudo sem tocar nos seus dados reais.

## Quick Start

### 1. Clonar e instalar

```bash
git clone https://github.com/karlfilho/homebeans.git
cd homebeans
uv sync
```

### 2. Testar o modo demo

Quer conhecer o projeto sem risco? Entre no modo demo e explore dados fictícios:

```bash
uv run homebeans mcp
```

Depois, no seu cliente MCP, peça algo como:

- `Ative o modo demonstração`
- `Inicie o tutorial guiado`
- `Mostre meu saldo atual`
- `Liste as transações recentes`

> O **modo demo** usa dados fictícios e preserva completamente o seu ledger real.

### 3. Usar a CLI

```bash
uv run homebeans add
uv run homebeans balance
uv run homebeans report
```

## Características

- **Partida dobrada**: cada centavo tem origem e destino, com validação automática.
- **Dados em YAML**: arquivo simples, local e fácil de inspecionar.
- **Integração com IA via MCP**: registre gastos, consulte saldos e gere relatórios por linguagem natural.
- **CLI interativa**: wizard guiado para adicionar transações.
- **Modo demonstração**: experimente sem risco.
- **Tutorial guiado**: onboarding prático direto no modo demo.

## Pré-requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

### Instalar o uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

No Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Instalação

```bash
git clone https://github.com/karlfilho/homebeans.git
cd homebeans
uv sync
```

Crie seu arquivo de configuração, se quiser personalizar o caminho do ledger:

```bash
cp .env.example .env
```

## Como funciona a partida dobrada

Partida dobrada é uma regra simples: **todo dinheiro que sai de algum lugar chega em algum lugar**. Cada transação precisa ter pelo menos dois lançamentos cuja soma final seja zero.

Exemplo: um café de R$ 10 pago em dinheiro.

- O dinheiro saiu da carteira → `ativos:carteira: -10.00`
- O gasto entrou em despesas → `despesas:alimentacao:cafe: +10.00`

Resultado:

```text
-10 + 10 = 0
```

### Tipos de conta

| Tipo | Para quê | Exemplos |
|---|---|---|
| `ativos` | O que você possui | carteira, banco, investimentos |
| `passivos` | O que você deve | cartão de crédito, empréstimos |
| `entradas` | De onde vem dinheiro | salário, freelance, aluguel |
| `despesas` | Para onde vai dinheiro | alimentação, moradia, transporte |
| `patrimônio` | Capital inicial | saldo inicial |

### Hierarquia de contas

As contas usam `:` como separador e aceitam até 3 níveis:

```text
despesas:alimentacao:mercado   ✓
ativos:banco                   ✓
despesas:a:b:c                 ✗
```

Para detalhes extras, use tags:

```text
veiculo:gol
viagem:sp
fornecedor:claro
```

## Usando a CLI

### Adicionar uma transação

```bash
uv run homebeans add
```

O wizard pergunta data, descrição, contas e valores, sugere contas já usadas e valida o balanço antes de salvar.

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

## Usando com um assistente de IA via MCP

O HomeBeans funciona como um **servidor MCP**, permitindo que assistentes de IA usem suas ferramentas diretamente.

### Iniciar o servidor

```bash
uv run homebeans mcp
```

### Exemplo de configuração no Claude Desktop

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\\Claude\\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "homebeans": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/caminho/para/homebeans",
        "homebeans",
        "mcp"
      ]
    }
  }
}
```

Depois disso, você pode pedir coisas como:

- “Registra um almoço de R$ 45 que paguei hoje.”
- “Qual foi meu gasto com alimentação este mês?”
- “Mostre o fluxo de caixa dos últimos 3 meses.”

## Ferramentas MCP

| Ferramenta | O que faz |
|---|---|
| `get_balance` | Saldo atual de todas as contas |
| `get_transactions` | Consulta com filtros |
| `get_recent_transactions` | Últimas N transações |
| `get_accounts_tree` | Árvore hierárquica |
| `get_tags_list` | Tags em uso |
| `get_ledger_stats` | Estatísticas gerais |
| `get_account_statement` | Extrato com saldo acumulado |
| `get_spending_summary` | Maiores gastos por categoria |
| `get_income_statement` | Entradas vs despesas |
| `get_balance_sheet` | Balanço patrimonial |
| `get_cashflow` | Fluxo de caixa |
| `add_transaction` | Adiciona transação |
| `edit_transaction` | Edita transação |
| `delete_transaction` | Remove transação |
| `clear_journal` | Apaga tudo com confirmação |
| `enter_demo_mode` | Ativa modo demo |
| `exit_demo_mode` | Sai do modo demo |
| `start_demo_tutorial` | Inicia tutorial guiado |

O parâmetro `period` aceita: `day`, `week`, `month`, `year` e `all`.

## Modo demonstração

Quer explorar sem tocar nos seus dados reais?

Peça ao assistente:

- `Ative o modo demonstração`
- `Inicie o tutorial guiado`

O tutorial apresenta a lógica da partida dobrada e conduz exercícios práticos com dados fictícios.

Para sair:

- `Saia do modo demo`

## Estrutura do projeto

```text
src/homebeans/
├── config.py
├── models.py
├── storage.py
├── mcp_server.py
├── cli.py
├── reports.py
└── demo_mode.py

src/core/
└── suggester.py

data/
├── ledger.yaml
└── demo_ledger_template.yaml
```

## Privacidade

O arquivo `data/ledger.yaml` fica local e está no `.gitignore`. Seus dados financeiros não sobem para o GitHub.

## Testes

```bash
uv run pytest tests/ -v
```

Atualmente o projeto tem **91 testes** cobrindo modelos, partida dobrada, modo demo, ferramentas MCP e relatórios.

## Contribuindo

Contribuições são bem-vindas. Veja o arquivo [CONTRIBUTING.md](CONTRIBUTING.md) para detalhes de ambiente, fluxo de branches e padrão de PR.

## Changelog

O histórico de mudanças está em [CHANGELOG.md](CHANGELOG.md).

## Licença

MIT

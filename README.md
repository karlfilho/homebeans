# HomeBeans

Sistema de Contabilidade de Partida Dobrada em Python, inspirado no [hledger](https://hledger.org/).

## Características

- **Partida dobrada**: validação rigorosa (Débitos + Créditos = 0)
- **Persistência em YAML**: formato legível, preserva comentários (Ruamel.YAML)
- **CLI moderna**: Typer + Rich com tabelas coloridas
- **Gráficos**: exportação para HTML via Plotly
- **Integridade**: Pydantic V2 garante esquema e cálculos corretos

## Pré-requisitos

- Python 3.11+
- [UV](https://docs.astral.sh/uv/) (gerenciador de dependências)

## Instalação

```bash
git clone https://github.com/karlfilho/homebeans.git
cd homebeans
uv sync
```

## Uso

### Adicionar transação

```bash
uv run homebeans add --date 2024-01-15 --desc "Salário" "assets:bank:5000" "income:salary:-5000"
```

Formato dos postings: `conta:valor` (positivo = débito, negativo = crédito).

### Balanço

```bash
uv run homebeans balance
```

### Relatório de transações

```bash
uv run homebeans report --limit 20
```

### Gráfico

```bash
uv run homebeans chart -o balance.html
```

## Configuração

Copie `.env.example` para `.env` e ajuste:

```
LEDGER_PATH=./data/ledger.yaml
```

## Estrutura

```
src/homebeans/
├── models.py    # Transaction, Posting (Pydantic)
├── storage.py   # Persistência YAML
├── reports.py   # Relatórios e balanços
├── viz.py       # Gráficos Plotly
└── cli.py       # Interface Typer
```

## Testes

```bash
uv run pytest tests/ -v
```

## Licença

MIT

## Estrutura do projeto

- **src/homebeans**
  - `__init__.py`: inicialização do pacote.
  - `cli.py`: interface de linha de comando (Typer) com comandos `add`, `balance`, `report`, `chart`.
  - `models.py`: modelos Pydantic (`Posting`, `Transaction`) e validações de partida dobrada.
  - `reports.py`: geração de relatórios de balanço por conta.
  - `storage.py`: leitura e escrita do livro-razão YAML.
  - `viz.py`: geração de gráficos de saldo por conta com Plotly.

- **src/core**
  - `suggester.py`: motor de sugestões para o wizard `hb add`, usando fuzzy matching (`thefuzz`) e histórico do livro-razão para sugerir conta e valor, além de extrair lista de contas para autocomplete.

- **tests**
  - `test_models.py`: testes dos modelos Pydantic e validações.
  - `test_integrity.py`: testes de integridade geral do sistema.


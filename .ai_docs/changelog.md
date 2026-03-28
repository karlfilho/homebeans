- **[2026-03-27] Tutorial guiado no modo demo (`start_demo_tutorial`)**
  - Adicionada tool MCP `start_demo_tutorial()` que retorna um roteiro completo para o assistente conduzir o usuário pelo HomeBeans.
  - Roteiro inclui: teoria rápida de partida dupla (5 pontos), 3 exercícios práticos usando o ledger demo, e encerramento.
  - `enter_demo_mode()` agora instrui explicitamente o assistente (via texto no retorno) a perguntar se o usuário quer o tutorial antes de prosseguir.
  - Exercícios cobrem: consulta de saldo/estatísticas, registro de despesa, análise de DRE e extrato de conta.

- **[2026-03-27] Ferramentas estatísticas MCP**
  - `get_ledger_stats()`: estatísticas gerais do ledger (total de transações, período, contas/tags distintas, média mensal).
  - `get_account_statement(account, start_date, end_date)`: extrato detalhado de uma conta com saldo acumulado linha a linha.
  - `get_spending_summary(period, start_date, end_date, top_n)`: maiores gastos por categoria de despesa com valor e percentual.
  - `get_recent_transactions(limit, account_filter, tag_filter)`: últimas N transações com filtros opcionais, sem precisar de filtro de data.

- **[2026-03-27] Modo de demonstração (`enter_demo_mode` / `exit_demo_mode`)**
  - Adicionado `src/homebeans/demo_mode.py` com estado em memória (`_demo_active`) e funções `enter_demo()` / `exit_demo()` / `is_demo_active()`.
  - `enter_demo()` copia `data/demo_ledger_template.yaml` para `data/demo_ledger.yaml` (arquivo de trabalho) e ativa o redirecionamento.
  - `exit_demo()` descarta o arquivo de trabalho e desativa o redirecionamento.
  - `get_ledger_path()` em `config.py` consulta `is_demo_active()` e retorna o caminho correto automaticamente — nenhuma outra tool precisou ser alterada.
  - Adicionadas tools MCP `enter_demo_mode()` e `exit_demo_mode()` ao servidor.
  - Template `data/demo_ledger_template.yaml` criado com 48 transações fictícias cobrindo Jan–Mar 2026: salário, aluguel, supermercado, restaurante, combustível, saúde, lazer, educação, freelance e poupança.
  - 14 testes em `tests/test_demo_mode.py` cobrindo: ativação, desativação, isolamento do ledger real, integridade do template (partida dobrada) e integração com `config.get_ledger_path()`.

- **[2026-03-15] Wizard interativo no `hb add` com sugestões**
  - Adicionado módulo `src/core/suggester.py` para sugerir conta e valor com base em descrições similares do histórico (fuzzy matching com `thefuzz`) e extrair lista de contas para autocomplete.
  - Refatorado comando `hb add` em `src/homebeans/cli.py` para um wizard interativo usando Questionary:
    - Perguntas guiadas para data, descrição e lançamentos.
    - Autocomplete de contas com base em todas as contas já usadas no histórico.
    - Sugestão automática de conta/valor quando há histórico com descrição similar.
    - Validação em tempo real via modelos Pydantic (`Posting` e `Transaction`).
    - Loop de lançamentos até o saldo da transação ficar exatamente zero, exibindo quanto falta para zerar após cada inserção.

- **[2026-03-15] Comandos de journal e contas + regra de sintaxe**
  - Adicionado `homebeans journal-clear` para limpar o journal com confirmação antes de sobrescrever o YAML.
  - Adicionado `homebeans accounts` para listar contas em uso por tipo, com filtros (`--a`, `--p`, `--d`, `--r`, `--o`) e visualização hierárquica (`--tree`).
  - Reforçada validação de `Posting.account` para exigir a sintaxe `tipo:subconta(:subconta...)` (hierarquia por `:` e sem espaços).


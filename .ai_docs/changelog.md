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


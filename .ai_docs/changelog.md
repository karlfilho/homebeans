- **[2026-03-15] Wizard interativo no `hb add` com sugestões**
  - Adicionado módulo `src/core/suggester.py` para sugerir conta e valor com base em descrições similares do histórico (fuzzy matching com `thefuzz`) e extrair lista de contas para autocomplete.
  - Refatorado comando `hb add` em `src/homebeans/cli.py` para um wizard interativo usando Questionary:
    - Perguntas guiadas para data, descrição e lançamentos.
    - Autocomplete de contas com base em todas as contas já usadas no histórico.
    - Sugestão automática de conta/valor quando há histórico com descrição similar.
    - Validação em tempo real via modelos Pydantic (`Posting` e `Transaction`).
    - Loop de lançamentos até o saldo da transação ficar exatamente zero, exibindo quanto falta para zerar após cada inserção.


# Contributing

Obrigado pelo interesse em contribuir com o HomeBeans.

## Ambiente

Requisitos:
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

Instalação local:

```bash
git clone https://github.com/karlfilho/homebeans.git
cd homebeans
uv sync
```

## Fluxo de trabalho

1. Faça um fork do repositório.
2. Crie uma branch descritiva:
   ```bash
   git checkout -b feat/nome-da-melhoria
   ```
3. Faça suas mudanças.
4. Rode os testes:
   ```bash
   uv run pytest tests/ -v
   ```
5. Commit com mensagem clara.
6. Abra um Pull Request explicando:
   - o problema resolvido;
   - a abordagem escolhida;
   - qualquer impacto em CLI, MCP ou modo demo.

## Diretrizes

- Preserve a consistência com a lógica de partida dobrada.
- Prefira mudanças pequenas e focadas.
- Atualize a documentação quando alterar comportamento visível ao usuário.
- Adicione ou ajuste testes sempre que mudar regras de negócio.

## Áreas úteis para contribuir

- Melhorias na CLI interativa
- Novos relatórios
- Experiência do modo demo
- Ergonomia das ferramentas MCP
- Documentação e exemplos

## Discussão

Para mudanças maiores, abra uma issue antes de implementar.

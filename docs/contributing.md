# Contribuindo com o Technology Park ABM

Obrigado pelo interesse. Este é um projeto de pesquisa em modelagem baseada
em agentes; mudanças de comportamento precisam de evidência, teste e
documentação.

## Antes de abrir uma mudança

1. Descreva o problema e o critério de aceitação testável.
2. Diga o que **não** está no escopo.
3. Se for mudança de mecanismo científico, registre a hipótese, a seed e o
   efeito esperado.
4. Se for mudança no laboratório, atualize as fontes em `docs/prototypes/`
   e o catálogo `investigation-scenarios.json`; rebuild e restart do servidor
   são parte da mudança.

## Verificação local

```bash
# Ambiente (lockfile-exato)
uv sync --extra dev --frozen

# Portões determinísticos (segundos)
uv run python scripts/check_gates.py

# Suíte de testes
uv run python -m pytest -q

# Runner completo (lint, tipos, testes, smokes, política de dados)
uv run python scripts/run_checks.py
```

Mudanças no laboratório exigem rebuild da página e restart do servidor
para refrescar a proveniência. Nenhum deploy público decorre de Git push.

## Definition of Done

- [ ] Spec curta: problema, comportamento esperado e critério de aceitação.
- [ ] Teste que falha antes e passa depois (ou justificativa explícita).
- [ ] Teste cobre o mecanismo, não apenas a linha: unidade + propriedade/
      invariante + metamórfico + golden/integração quando aplicável.
- [ ] `check_gates.py` exit 0.
- [ ] Suíte verde quando `src/`, `scripts/` ou `tests/` mudar.
- [ ] Laboratório verde quando `docs/prototypes/` mudar (rebuild + testes
      do workbench).
- [ ] Documentação viva atualizada (README, ODD/TRACE, cenários, docs).
- [ ] Nenhum artefato de build/resultado no índice git.
- [ ] Goldens só mudam de propósito, com motivo no commit.

## Estilo

- Python: funções claras, sem aleatoriedade global; use fluxos derivados da
  seed (`config.py`).
- Testes: determinísticos, com seeds explícitas; sem retries silenciosos.
- JS do laboratório: nativo, sem dependências de build; PT-BR com acentos.
- Commits pequenos, no imperativo, sem misturar refactor com mudança de
  comportamento.

## O que não fazer

- Enfraquecer teste/gate para fazer a verificação passar.
- Editar CSV/JSON exportado para "corrigir" um número.
- Commitar `outputs/`, resultados, `data/raw`, `data/processed` ou microdados.
- Adicionar dependência sem justificar versão, licença e manutenção.
- Publicar rascunhos, pareceres ou material de revisão no repositório
  público.

## Pull requests

PRs são bem-vindos. Para mudanças grandes, abra uma issue primeiro. Inclua no
PR: motivação, o que mudou, como testar e quais limites continuam valendo.

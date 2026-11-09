# Reprodutibilidade — Technology Park ABM

> Guia público. O material de revisão é mantido no repositório privado;
> aqui ficam o código, os comandos e as evidências regeneráveis.

## Ambiente

| Componente | Versão de referência | Observação |
|---|---|---|
| Python | 3.12.10 local | `pyproject.toml` declara Python 3.12+ |
| Mesa | 3.5.1 | pin `mesa>=3.5,<4` (ADR 0010) |
| networkx | 3.7 | dependência de runtime |
| uv | 0.11+ | `uv.lock` versionado; `uv sync --extra dev --frozen` reproduz o ambiente |

O `uv.lock` é versionado e garante a árvore exata de dependências. O fluxo
clássico com `pip install -e ".[dev]"` também funciona. Não adicione
dependências sem atualizar o `pyproject.toml` e registrar o motivo.

## Determinismo

- Uma semente mestra deriva fluxos independentes por processo
  (`config.py`); nada de aleatoriedade global ou relógio no caminho de
  simulação.
- Trajetórias douradas (`tests/test_regression.py`) congelam o
  comportamento; qualquer mudança exige justificativa deliberada.
- Reprodução byte-idêntica: mesma semente + parâmetros + versões reproduz
  os mesmos bytes (`tests/test_reproduction.py`).

## Comandos canônicos

```bash
# 1. Instalar
uv sync --extra dev --frozen

# 2. Portões determinísticos
uv run python scripts/check_gates.py

# 3. Suíte de testes
uv run python -m pytest -q

# 4. Runner local (lint, tipos, testes, smokes, política de dados)
uv run python scripts/run_checks.py
```

## Laboratório

```bash
# 1. Gerar a página (88 execuções, 11 opções)
uv run python scripts/build_investigation_prototype.py

# 2. Servir em loopback
uv run python scripts/serve_investigation_prototype.py --port 8777
# http://127.0.0.1:8777 — escuta só em loopback
```

O servidor recusa subir se a página estiver desatualizada (guarda de
frescura): rebuild antes de servir. A prova de deploy é o health
(`version` + `git_commit` via `/api/investigation/health`).

## Corpus

Não há corpus de CSVs versionado: os resultados vivem em `results/`
(gitignored) e são regenerados pelos runners (`experiments.py`,
`sensitivity.py`) com sementes explícitas. Os manifests registram
parâmetros, versões, commit e identificação do roteiro (ADR 0003).

Regeneração de referência: `docs/final-report.md` (vereditos H1–H6),
`docs/validation-report.md`, `docs/sensitivity-report.md`.

## Proveniência

O fluxo é:

```
configuração → semente → trajetória → manifest → número
```

- `scripts/check_gates.py` — G1–G9, G13, G16 (lint, tipos, determinismo,
  dados, metadados).
- `scripts/run_checks.py` — bateria local completa (inclui política de
  dados: nada de `data/raw`, `data/processed` ou `results` no git).
- `tests/test_regression.py` — goldens congelados.
- `tests/test_gates.py` — identidade da página servida (sha + carimbo de
  build) e prova de saúde do sistema.

## Artefato

- Código: este repositório (MIT).
- Dados: `results/` não versionado; só agregados públicos em
  `data/manifest.json`.
- Citação: `CITATION.cff` (+ `codemeta.json`, `.zenodo.json`).
- Figuras: geradas pelo laboratório e exportadas em JSON/CSV com
  proveniência.

## Limites

- A calibração usa padrões qualitativos, não estimativas de parques reais.
- A faixa p10–p90 entre sementes não é intervalo de confiança.
- Vereditos de tendência descrevem a trajetória simulada, não provam
  causalidade.
- O horizonte do laboratório é finito (até 80 períodos): resultados são
  trajetórias, não equilíbrio.

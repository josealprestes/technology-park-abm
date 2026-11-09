# Technology Park ABM — Laboratório de Investigação de Parques Tecnológicos

> **Aviso:** este é um simulador **exploratório** de parques tecnológicos e
> retornos crescentes. Os resultados **não** constituem medição empírica,
> previsão de desempenho de parques reais, nem recomendação de política
> pública. Veja [Limites metodológicos](#limites-metodológicos).

![License](https://img.shields.io/badge/license-MIT-blue)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Tests](https://img.shields.io/badge/tests-335-brightgreen)
![Gates](https://img.shields.io/badge/gates-13%2F13-brightgreen)

---

## Sobre

**Technology Park ABM** é um modelo baseado em agentes (Mesa, Python) que
investiga sob quais condições as interações entre startups, empresas-âncora,
universidades, investidores, trabalhadores e governança geram retornos
crescentes — e quando congestão, concentração ou fragilidade institucional
revertem esses ganhos.

O modelo parte de **padrões qualitativos de aglomeração**: massa crítica que
adens a rede de parcerias, âncoras que difundem conhecimento quando
participam, infraestrutura compartilhada que sustenta encontros — até o
limiar em que a demanda supera a capacidade e cada organização passa a
pagar custo extra. O horizonte é finito (até 80 períodos por execução, no
laboratório); o objeto é a **trajetória**, não o equilíbrio.

O projeto combina três camadas:

1. **Simulador científico** em Mesa, com sementes explícitas e trajetórias
   douradas (goldens) determinísticas.
2. **Laboratório de investigação** em quatro etapas (Entender → Preparar →
   Explorar → Concluir): onze roteiros de partida, parâmetros editáveis,
   execução local com sementes pareadas e dossiês conceituais com fontes.
3. **Instrumentos de reprodutibilidade**: experimentos E1–E7, análise de
   sensibilidade (Morris/Sobol), manifests com proveniência e exportação de
   evidências (JSON/CSV).

O material de revisão é mantido à parte, no repositório privado. Este
repositório público contém código, testes, laboratório, documentação de
modelo e instrumentos de reprodutibilidade.

---

## Laboratório no navegador

O laboratório é gerado localmente (dados e fontes embutidos, zero
dependências no navegador) e servido em loopback:

```powershell
uv sync --extra dev --frozen
.venv/Scripts/python.exe scripts/build_investigation_prototype.py
.venv/Scripts/python.exe scripts/serve_investigation_prototype.py --port 8777
```

Abra `http://127.0.0.1:8777`. Escolha **observar um cenário** ou **comparar
dois**. Onze roteiros de partida, em três grupos:

| Roteiro | Pergunta | O que observar |
|---|---|---|
| **Massa crítica** | Mais startups geram só mais atividade ou mudam a interação? | parcerias produtivas, conhecimento médio, sobrevivência (8 vs 16) |
| **Âncora ativa** | A presença da âncora basta ou ela precisa participar? | laços da âncora, conhecimento, inovação (ativa vs passiva) |
| **Diversidade** | Setores diferentes formam relações produtivas? | relações acima do limiar, conhecimento, inovação |
| **Capacidade** | O que acontece quando a demanda supera a infraestrutura? | congestionamento, capital, saídas (capacidade 8 vs 24) |
| **Conexão** | Facilitar encontros muda os resultados? | relações, conhecimento, inovação (matchmaking 0,5 vs 0) |
| **Choque** | O que muda depois da saída de uma organização central? | saídas efetivas, população, reconexão (com vs sem choque) |

A etapa Concluir traz **síntese e vereditos de Mann-Kendall** por indicador
(direção, magnitude, janela, p): séries curtas declaram "sem veredito", e
congestão acima de 1 levanta o alerta de saturação. Veredictos rodam sobre
a média entre sementes; a faixa p10–p90 não é intervalo de confiança.

> O carimbo de versão no cabeçalho (`v1.0.0`) identifica a edição servida;
> commit, boot e hash da página estão em `/api/investigation/health`.

---

## Como executar

### Pré-requisitos

- **Python 3.12+** (referência local: 3.12.10)
- Navegador moderno para o laboratório

### Instalação

```bash
git clone https://github.com/josealprestes/technology-park-abm.git
cd technology-park-abm
uv sync --extra dev --frozen
```

O `uv.lock` é versionado e reproduz a árvore exata de dependências; o venv
clássico com `pip install -e ".[dev]"` também funciona.

### Simulação rápida

```bash
uv run python -m technology_park_abm                     # demonstração determinística
uv run python -m technology_park_abm.experiments E3 --seeds 1 2 3 --periods 60
```

### Laboratório local

```bash
uv run python scripts/build_investigation_prototype.py   # gera a página (88 execuções, 11 opções)
uv run python scripts/serve_investigation_prototype.py --port 8777
# http://127.0.0.1:8777 — escuta só em loopback
```

O servidor recusa subir se a página estiver desatualizada (guarda de
frescura): rebuild antes de servir. Uma execução por vez; trabalhos e
rascunhos vivem em memória — exporte a evidência desejada (JSON esquema 4,
CSV esquema 2 com p0).

---

## Testes e verificação local

A verificação canônica é **local**:

```bash
uv run python scripts/run_checks.py          # lint, tipos, testes, smokes
uv run python scripts/check_gates.py          # portões determinísticos G1–G9, G13, G16
uv run python -m pytest -m gate -q           # subconjunto rápido: 13/13
uv run python -m pytest -m regression -q     # trajetórias douradas (goldens congelados)
```

A suíte cobre unidade, propriedades/invariantes (Hypothesis), metamórfico,
goldens, integração, contrato e reprodução byte-idêntica. Cobertura mínima
de 90% (medida: 93,89% no subconjunto sem navegador; e2e do laboratório à
parte). Cobertura sozinha **não** é usada como critério de qualidade.

---

## Reprodutibilidade

- **Determinismo por semente:** uma semente mestra deriva fluxos
  independentes por processo (`config.py`); nada de aleatoriedade global ou
  relógio no caminho de simulação.
- **Trajetórias douradas:** `tests/test_regression.py` congela o
  comportamento; qualquer mudança exige justificativa deliberada.
- **Manifestos:** cada execução registra parâmetros, sementes, versões,
  commit e identificação do roteiro (ADR 0003; campos STRESS verificados).
- **Metadados:** `CITATION.cff`, `codemeta.json` e `.zenodo.json`
  sincronizados com `pyproject.toml` (portão G16).
- **Dados:** só agregados públicos versionados (`data/manifest.json`,
  com base legal e nível de dados pessoais por fonte); microdados ficam
  fora do repositório (LGPD, ADR 0012).
- **Nunca** "conserte" um número editando exportação; regenere pela
  execução e documente a divergência.

Detalhes operacionais: [`docs/test-plan.md`](docs/test-plan.md).

---

## Como o motor funciona

### Agentes

Cada `Startup` tem capital, qualidade tecnológica, conhecimento, reputação,
equipe, setor e idade; `AnchorFirm` (participação passiva/ativa),
`University`, `Investor`, `Worker` (habilidade, escolaridade) e
`ParkAuthority` (política, reputação) completam o elenco.

### Ordem dos dez passos

1. Entradas de organizações. 2. Infraestrutura e políticas. 3. Formação e
   dissolução de relações. 4. Alocação de recursos (P&D vs mercado).
5. Difusão de conhecimento. 6. Investimento e contratação. 7. Receitas,
   custos e congestão. 8. Saídas tipadas (falha, aquisição, voluntária,
   migração). 9. Reputação coletiva. 10. Registro de métricas.

### Métricas

| Métrica | O que é | Leitura |
|---|---|---|
| `active_startup_count` | startups presentes | população |
| `productive_tie_count` | parcerias acima do limiar de força | interação efetiva |
| `knowledge_mean` | estoque médio por startup ativa | aprendizado |
| `innovation_cumulative` | eventos acumulados | novidade |
| `capital_total` | capital das ativas | folga financeira |
| `congestion` | demanda / capacidade | saturação (acima de 1 há custo extra) |

A definição de parceria produtiva usa o limiar efetivamente configurado; se
A e B usarem limiares distintos, o delta desse indicador fica indisponível
— mudar a régua não implica mudar a rede.

---

## Cenários e hipóteses

| Hipótese | Pergunta | Veredito (E1–E7) |
|---|---|---|
| H1 massa crítica | Mais agentes complementares formam mais parcerias? | Suportada com teto (acima da capacidade, colapsa) |
| H2 diversidade | Complementaridade setorial gera mais inovação? | Inconclusiva (efeito transitório) |
| H3 âncora | Spillovers exigem participação ativa? | Parcial, com custo de congestão |
| H4 instrumentos | Infraestrutura de conexão supera subsídio à entrada? | Suportada nos contrastes E4 |
| H5 congestão | Retornos crescentes têm limiar? | Suportada (custo extra acima de 1) |
| H6 resiliência | Redes distribuídas absorvem a perda central? | Inconclusiva por desenho (E7 quantifica) |

Os roteiros do laboratório exploram esses mecanismos sem revisar os
vereditos, registrados em [`docs/final-report.md`](docs/final-report.md).

---

## Para gestores e pesquisadores

O laboratório permite explorar perguntas como:

- A partir de que tamanho o parque deixa de ganhar com mais entradas?
- Quando a âncora participa de fato da rede, e quando fica isolada?
- Facilitar encontros (matchmaking) gera inovação ou só mais relações?
- O que acontece com capital e população depois de um choque central?
- Universidades ativas mudam o conhecimento médio das empresas?

Glossário de parâmetros e dossiês com fontes: etapa Entender do laboratório
(`docs/prototypes/investigation-scenarios.json`, 19 referências).

---

## FAQ

### Preciso de internet para simular?
Não. Apenas instalação de dependências. O laboratório roda em loopback.

### Posso usar meus próprios dados?
Para pesquisa, mas isso é um novo desenho de calibração/validação, não uma
extensão automática. Microdados ficam fora do repositório (LGPD); veja
`docs/lgpd-microdata-study.md` e `docs/data-contracts.md`.

### A faixa p10–p90 é intervalo de confiança?
Não. É a dispersão entre as sementes executadas — descreve variabilidade
do experimento, não incerteza sobre um parque real.

### O veredito de tendência prova que o mecanismo funciona?
Não. O teste de Mann-Kendall descreve a trajetória simulada; a regra que a
gerou é premissa do modelo, não descoberta do teste.

### O laboratório substitui os experimentos E1–E7?
Não. Comparações exploratórias preparam intuição; os vereditos H1–H6 vêm
dos protocolos registrados.

### Como contribuir?
Veja [`CONTRIBUTING.md`](CONTRIBUTING.md). Mudanças de comportamento exigem
teste que falhe antes e passe depois; goldens mudam só de propósito, com
motivo no commit.

---

## Arquitetura

```
technology-park-abm/
├── src/technology_park_abm/
│   ├── model.py              # Mesa, ordem dos 10 passos, métricas
│   ├── agents.py             # startups, âncoras, ICTs, investidores, workers
│   ├── environment.py        # setores, infraestrutura, mercados, política
│   ├── network.py            # laços tipados com força
│   ├── metrics.py            # métricas, Mann-Kendall, diagnósticos
│   ├── workbench_core.py     # kernel do laboratório (parâmetros, cenários, vereditos)
│   ├── investigation.py      # execuções semeadas observe/compare
│   ├── experiments.py        # E1–E7 com manifests
│   ├── sensitivity.py        # OAT, Morris/Sobol
│   └── validation.py         # validação orientada a padrões
├── scripts/                  # build/serve do laboratório, gates, pipeline de dados
├── tests/                    # unidade, propriedades, goldens, integração, portões
├── docs/
│   ├── prototypes/           # fontes do laboratório + catálogo científico
│   └── adr/                  # decisões 0001–0006, 0010–0013
├── data/manifest.json        # catálogo de fontes públicas
├── pyproject.toml / uv.lock
├── CITATION.cff
└── README.md
```

### Stack

| Camada | Tecnologia | Versão/nota |
|---|---|---|
| Núcleo | Python | 3.12+ |
| ABM | Mesa | >=3.5,<4 (ADR 0010) |
| Rede | networkx | 3.x |
| Testes | pytest + Hypothesis | propriedades derandomizadas |
| Tipos | mypy strict + ty + pyrefly | portão G3 |
| Qualidade | ruff + portões G1–G9, G13, G16 | `scripts/run_checks.py` |
| Laboratório | HTML/JS nativo | gerado, embutido, sem build no navegador |

---

## Limites metodológicos

- O simulador é **exploratório**: parâmetros calibrados para padrões
  qualitativos, não estimados de parques reais.
- A calibração usa **agregados públicos**, não microdados proprietários.
- A validação é **macro** (padrões: heterogeneidade, sobrevivência,
  clustering); micro-mecanismos não foram observados em campo.
- O horizonte do laboratório é finito (até 80 períodos): resultados são
  **trajetórias**, não equilíbrio.
- Vereditos H1–H6 valem para os protocolos E1–E7; o laboratório não os
  revisa.

---

## Validação e robustez

- **E1–E7:** experimentos registrados com distribuições por semente e
  manifests com proveniência.
- **Goldens:** trajetórias congeladas; reprodução byte-idêntica entre
  processos.
- **Sensibilidade:** OAT + Morris/Sobol com validação cruzada contra SALib.
- **Validação:** hierarquia em níveis (código, processo, padrões,
  distribuições); validação empírica em nível de parque documentada como
  inviável com dados públicos.
- **Testes:** 335 coletados, goldens, metamórfico, mutação 96,4% (núcleo
  medido) e 13 portões determinísticos.

---

## Contexto acadêmico

Este projeto foi desenvolvido como um dos trabalhos finais da disciplina
**IA006J — Tópicos em Sistemas Inteligentes II, Turma I** ("Aplicações da
Ciência e Engenharia dos Sistemas Dinâmicos de Muitos Agentes"), oferecida
pelo Programa de Pós-Graduação da **Faculdade de Engenharia Elétrica e de
Computação (FEEC) da Unicamp**, cursada como aluno regular de mestrado no
2º semestre de 2026.

A disciplina conecta a trajetória profissional do autor — que percorre
Direito, Tecnologia e Gestão — à pesquisa acadêmica em sistemas complexos e
modelagem baseada em agentes. As perguntas do simulador nascem tanto da
prática profissional quanto da investigação acadêmica sobre adesão a normas,
comportamento organizacional e difusão cultural.

---

## Metodologia de desenvolvimento (vibe coding)

Este projeto foi desenvolvido utilizando **vibe coding**, uma abordagem de
codificação iterativa e dialógica mediada por Inteligência Artificial
Generativa (IA Gen), na qual a IA atua como parceira no processo criativo e
formativo (de Lima Prestes, 2025a). O código foi gerado, revisado e refinado
por meio de interações em linguagem natural com modelos de linguagem, com
supervisão e direção humana em todas as etapas.

Cada funcionalidade seguiu o ciclo definido no **Framework para Letramento
Crítico em IA** (de Lima Prestes, 2025b): **intenção → prompt → geração →
análise crítica → metacognição → autoria → iteração**. O processo busca
reduzir Carga Extrínseca e ampliar Carga Germana (Sweller, 1988; 2010;
Grazioli, 2025), de modo que o uso da IA não substitua o raciocínio, mas o
potencialize.

No plano operacional, o vibe coding foi acompanhado de disciplina de
engenharia: especificações curtas, gates determinísticos (G1–G9), testes de
unidade/propriedade/metamórficos/golden, mutation testing,
revisão humana e proveniência de cada número. A IA acelera a geração e a
revisão; a responsabilidade científica permanece humana.

### Referências da metodologia

> de Lima Prestes, J. A. (2025a). *Vibe Coding e Ensino Humanizado com IA:
> Uma Proposta Inclusiva para a Formação em Engenharia*. COBENGE 2025.
> DOI: [10.37702/2175-957X.COBENGE.2025.6030](https://doi.org/10.37702/2175-957X.COBENGE.2025.6030)

> de Lima Prestes, J. A. (2025b). *Vibe Coding na Educação Superior:
> Framework para Letramento Crítico em IA*. SciELO Preprints.
> DOI: [10.1590/SciELOPreprints.15198](https://doi.org/10.1590/SciELOPreprints.15198)

---

## Licença

MIT License. Copyright (c) 2026 José Augusto de Lima Prestes. Veja
[`LICENSE`](LICENSE).

---

## Citação

```bibtex
@software{prestes2026technologyparkabm,
  author = {Prestes, Jos{\'e} Augusto de Lima},
  title = {Technology Park ABM: Laborat{\'o}rio de Investiga{\c{c}}{\~a}o de
           Parques Tecnol{\'o}gicos},
  year = {2026},
  url = {https://github.com/josealprestes/technology-park-abm},
  note = {Projeto de pesquisa em ABM; disciplina IA006J, FEEC/Unicamp.}
}
```

---

## Links

- **Site:** [joseprestes.com](https://joseprestes.com)
- **ORCID:** [0000-0001-8686-5360](https://orcid.org/0000-0001-8686-5360)
- **Currículo Lattes:** [8295411061159606](http://lattes.cnpq.br/8295411061159606)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)
- **Contribuição:** [docs/contributing.md](docs/contributing.md)
- **Reprodutibilidade:** [docs/REPRODUTIBILIDADE.md](docs/REPRODUTIBILIDADE.md)

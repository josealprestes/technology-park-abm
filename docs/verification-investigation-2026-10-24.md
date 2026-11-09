# Verificação do laboratório de investigação — 24/10/2026

Escopo: quatro iterações de jornada e revisão da seleção científica, baseadas
no checkout posterior à v2.13.0. A versão instalada continua 2.13.0; alterações
estão em `CHANGELOG.md` sob Unreleased. Este registro não constitui release,
deploy, validação empírica ou avaliação com participantes.

## Ambiente e comandos

- Windows, Python 3.12.10 de `C:/Python312`, `.venv` com dependências de
  `uv.lock`; ambiente anterior recriado após falha de OpenSSL do interpretador
  automaticamente selecionado, sem alteração do lockfile.
- Playwright/Chromium instalados; testes de navegador efetivamente executados.
- `python scripts/run_checks.py`: lint, formato, mypy, ty, pyrefly, suíte com
  warnings como erros e cobertura, três smokes e política de dados.
- Gerador: `python scripts/build_investigation_prototype.py`.
- Operação: `python scripts/serve_investigation_prototype.py --port 8777`.
- Não foram executados notebooks de IA006J, novas campanhas E1–E7, mutação,
  serviços remotos ou publicações nesta revisão.

## Evidência técnica da implementação

`outputs/checks-research.log` registra **506 testes aprovados em 308,30 s**,
cobertura **93,64%** (piso 90%), cinco verificações estáticas, smokes do pacote,
E5 e sensibilidade e política de dados verdes. Os onze testes da prévia estão
em `tests/test_investigation_prototype.py`, incluindo preservação dos nove
conjuntos originais, execução dos contrastes, fontes na exportação e ausência
de execução ao preparar uma comparação. Goldens e mecanismos não mudaram.

Inspeção adicional: onze dossiês e referências abertos em 1440, 320 e 412 px,
33 estados, sem overflow, violações axe, erros JavaScript ou requisições
externas. Logs/capturas locais: `outputs/qa-research.log` e
`outputs/investigation-evidence-v4/`. Foram inspecionadas capturas de massa
crítica, universidade e conferência da comparação.

O HTML servido em loopback foi comparado integralmente ao arquivo gerado:
1.335.718 bytes no fechamento dessa iteração. Health declarou schema 3 e 25
hashes foram conferidos contra os arquivos atuais. Tamanho e hash podem mudar
ao reconstruir porque commit, árvore e fontes entram na proveniência.

## Evidência que acompanha o Git

Consolidação documental: README, AGENTS, produto/design, handoff, planos,
arquitetura, operação/API, contribuições, validação e rascunho de publicação
foram reconciliados com o estado atual. Índice em `docs/README.md`. A auditoria
de 65 arquivos Markdown não encontrou links locais quebrados; referências a
capturas históricas foram identificadas como artefatos locais, sem links
para arquivos ausentes do repositório.

Revalidação após essa consolidação: `scripts/check_gates.py` passou com
**506 testes em 189,96 s**, cobertura **93,64%**, lint, formatação e mypy
verdes (`outputs/checks-docs-gates.log`). O runner estático adicional verificou
também ty e pyrefly. As quebras de linha de três fontes novos foram
normalizadas para LF antes do commit; não houve alteração de comportamento.
Após a normalização, os onze testes focados passaram em 48,56 s
(`outputs/checks-docs-prototype-final.log`) e as cinco verificações estáticas
voltaram a passar (`outputs/checks-docs-static-final.log`).
Metadados de pacote, instalação, CITATION, CodeMeta e Zenodo foram conferidos
em 2.13.0. Nenhuma nova versão ou tag é criada por esta sincronização.

Código, testes, catálogo de 19 referências, relatório científico, planos e
instruções de reprodução são versionados. Logs, capturas, HTML gerado, resultados,
venv, caches e PDFs da disciplina são artefatos locais; ficam fora do Git.
Os materiais de IA006J foram consultados somente para orientar a revisão;
o acervo acadêmico e suas respostas não foram copiados para este repositório.

Uma cópia limpa pode repetir os testes e reconstruir a prévia com os comandos
acima. As capturas históricas referenciadas no relatório não estão disponíveis
automaticamente em outra máquina. Os resultados de inspeção aqui registrados
são um recibo de execução, não garantia de usabilidade ou acessibilidade completa.

## Limites mantidos

Resultados são simulações; referências teóricas e aplicações de outros autores
não validam nossos parâmetros. Confirmação de H1–H6 exige desenhos e evidências
próprios. Leitor de tela real, compreensão, sucesso de tarefa, calibração e
validação histórica de parques permanecem avaliações distintas e pendentes.
Operação/API e limites interativos estão em
[`investigation-workbench.md`](investigation-workbench.md).

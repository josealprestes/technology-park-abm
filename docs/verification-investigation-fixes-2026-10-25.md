# Correções A1–A5 do laboratório — 25/10/2026

**Situação: cinco correções implementadas e aceites locais aprovados.**
Legibilidade em projetor real e compreensão humana continuam avaliações distintas.

Escopo: laboratório opcional, Unreleased, sobre o commit `8e05775` com
alterações locais. A versão instalada permanece 2.13.0. Este trabalho atende
à autorização do autor para corrigir a
[análise adversarial](adversarial-investigation-2026-10-25.md), sem release,
deploy remoto ou mudança do modelo, de H1–H6, dos padrões ou dos goldens.

Pergunta de engenharia: como permitir edição e compartilhamento sem confundir
mudança de definição da medida, mudança do comportamento e perda de contexto?
Os efeitos esperados são delta indisponível sob definições incompatíveis,
reprodução a partir do CSV, escopo junto da figura e recuperação legível de erro.

## Mudanças e oráculos de aceitação

| Achado | Correção | Evidência exigida |
| --- | --- | --- |
| A1 | Unidade derivada do limiar efetivo; definições distintas em A/B suspendem delta, contagem pareada e frase de diferença. As contagens individuais permanecem. Outros indicadores continuam comparáveis. JSON registra `measurement`. | `test_measurement_definitions_follow_config_and_guard_deltas`, três casos: limiares 0/1 com mapas idênticos, 0,5 comum e observação com limiar 0,7. Verifica contagem diretamente pelas forças das relações; alternar para capital recupera delta válido. |
| A2 | CSV schema `investigation-trajectories-2`, com configuração semeada por linha, proveniência, versão, commit e definição de medida, além de p0. Campos com aspas/vírgulas são escapados. | `test_csv_alone_reproduces_each_condition_seed_and_initial_state`, observar/comparar, quatro sementes: reconstruir trajetórias com o CSV, conferir todas as seis métricas em p0 e p0–p11, preservar precisão e bytes em exportações repetidas. |
| A3 | Título, cenários, valores, escopo de simulação/período/sementes/N, unidade e legenda pertencem à mesma figura. A descrição acessível também leva o escopo. | `test_figure_carries_scope_and_mobile_reading_has_16px_floor`, observar/comparar com N=1/4; inspeção visual da figura isolada em 1440/320/360/412 px. |
| A4 | Falha do `fetch` explica em PT-BR como verificar o servidor e repetir, preservando o rascunho. Validação HTTP continua exibindo a mensagem do servidor. | `test_transport_error_is_actionable_and_retry_preserves_draft`: abortar transporte, conferir texto/campos/botão e executar com sucesso após restabelecer a rede. |
| A5 | Definição, escopo e legenda têm piso de 16 px; no móvel o piso cobre os avisos e textos de leitura essenciais. | Medidas de estilo computado em 320/360/412 px, reflow e axe; inspeção visual. Projeção real e compreensão com pessoas permanecem manuais. |

As quatro funções novas produzem sete casos de regressão. O contrato de
linhas do CSV foi atualizado deliberadamente: `condições × N × (cursor + 1)`.
O JSON schema 3 recebe somente o campo aditivo `measurement`; seus registros
iniciais e históricos continuam preservados. A repetição da configuração e
da proveniência torna o CSV maior, em troca de poder reproduzi-lo sem outro
download. O código-fonte não é embutido na saída: a revisão e os hashes
identificam a cópia de código que deve ser preservada.

## Inspeção da interface servida

Prévia reconstruída e servidor local reiniciado, em 8777. No caso adversarial
semente 42/p20/limiares 0 e 1: A permanece 42,0 e B 0,0, o delta é “—” e a
conclusão explica por que não se calcula uma diferença sob uma definição comum.
O JSON conserva `comparable: false` e ambos os limiares. O CSV desse caso
tem 42 linhas, contando p0 em A e B, com os metadados de cada condição.

Capturas da figura isolada foram inspecionadas em 1440/320/360/412 px;
sem overflow de página, com definição/escopo/legenda em 16 px. Nos percursos
instrumentados não houve erro JavaScript não tratado nem requisição externa.
Evidências locais (não versionadas) em `outputs/adversarial-2026-10-25/`:
`fixes-visual.js`, `fixes-visual.log`, `fixes-figure-*.png`, `fixes-live.json`,
`fixes-live.csv`, logs do gerador/servidor e das verificações.

## Verificação técnica

`python scripts/run_checks.py`: **513 testes aprovados em 214,37 s**, cobertura
**93,64%**, lint, formato, mypy, ty, pyrefly, três smokes e política de dados
verdes. São 18 casos do laboratório, incluindo os sete novos aceites. O primeiro
ensaio focado encontrou uma leitura da tabela dentro de `<details>` ainda
fechado no próprio teste; abrir a tabela antes da asserção resolveu essa falha,
e a suíte completa acima validou a versão final. Log: `fixes-checks.log`.

O runner independente `python scripts/check_gates.py` também passou:
**513 testes em 196,73 s**, cobertura **93,64%**, lint, formato e mypy verdes
(`fixes-gates.log`). Os gates G1–G17 existentes permanecem verdes; não se
criou gate novo nem se afrouxou um oráculo para aceitar as correções.
O servidor responde HTTP 200, serve HTML idêntico ao arquivo reconstruído e
seus 25 hashes de fontes coincidem com a cópia testada. Na execução anterior
ao commit, a proveniência declarou `git_dirty: true`, corretamente: o recibo
registra aquele snapshot, não o estado posterior da sincronização Git.
Metadados de pacote/citação permanecem 2.13.0. Os 17 arquivos
Markdown modificados/novos com documentação e skills tiveram seus links locais
conferidos, sem destino ausente; `git diff --check` também passou. Os arquivos
do modelo e `tests/test_regression.py` não têm alteração no diff.

## Consolidação documental e sincronização

A pedido do autor, a documentação de entrada, roadmap, planos, arquitetura,
produto/design, acessibilidade, contribuição, validação e rascunho de publicação
foi reconciliada com os 513 testes e os aceites A1–A5. Números históricos
permanecem nas seções datadas; nenhum resultado científico foi promovido.
Código, testes, skills e estes documentos integram a mesma mudança. HTML,
logs, capturas, exportações, ambientes e dados brutos ficam fora do Git.

Na consolidação, os **75 arquivos Markdown** versionados ou preparados para
versionamento foram auditados, sem links locais quebrados. `run_checks.py
--fast` aprovou lint, formato, mypy, ty e pyrefly; `pytest -m gate -q`
aprovou **108 testes** em 35,51 s (405 fora dessa seleção). Os 25 hashes dos
fontes testados coincidem com os fontes a sincronizar; o código e os testes
não foram modificados nesta etapa documental. A suíte completa de 513 testes
acima permanece o recibo da implementação, não uma alegação de nova execução
completa a cada ajuste documental. Metadados continuam em 2.13.0.

A sincronização deve conferir `HEAD`, `origin/main`, `git ls-remote` e API
GitHub (commit e árvore), repositório privado e árvore local limpa. Depois
do commit, reconstruir o HTML e reiniciar o servidor para que novas exportações
registrem a revisão final e `git_dirty: false`; o snapshot pré-commit acima
continua sendo evidência histórica. Nenhuma versão, tag ou publicação remota
do laboratório é criada por essa sincronização.

Nenhum resultado técnico implica validação empírica, confirmação de hipótese,
compreensão humana ou legibilidade em projetor real. A entrega não modifica o
dashboard lançado nem encerra o trabalho UJ2 da interface publicada.

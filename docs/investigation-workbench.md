# Laboratório de investigação: uso e operação local

Estado em 24/10/2026: alternativa funcional e ainda não lançada ao dashboard
v2.13.0. Jornada: **Entender → Preparar → Explorar → Concluir**. Há onze opções:
nove configurações originais, uma variação de capacidade e massa crítica.
A revisão de nomes, referências e desenhos está em
[`scenario-sota-review.md`](scenario-sota-review.md).

## Iniciar em uma cópia do repositório

Na raiz do projeto, com Python >= 3.12 e o ambiente instalado:

```powershell
uv sync --extra dev --frozen
.venv/Scripts/python.exe scripts/build_investigation_prototype.py
.venv/Scripts/python.exe scripts/serve_investigation_prototype.py --port 8777
```

Abrir `http://127.0.0.1:8777/`. O processo fica no terminal; `Ctrl+C` o encerra.
A porta pode ser alterada com `--port`. O servidor aceita somente loopback.
Se a porta estiver ocupada, escolher outra ou encerrar o processo identificado
como pertencente a esta prévia. A instalação clássica documentada em
[`contributing.md`](contributing.md) também funciona.

O gerador calcula 88 execuções: onze configurações, sementes 1–8, 80 períodos.
São 891 quadros de rede, p0–p80 da primeira semente de cada configuração.
Fontes Geist, código e dados compactados ficam no HTML gerado em
`outputs/investigation/index.html`. Esse arquivo e resultados não entram no Git.
O navegador precisa suportar `DecompressionStream` para abrir os dados.

Abrir o HTML diretamente ou servi-lo por um servidor de arquivos permite
explorar os exemplos registrados. **Personalização requer o servidor de
investigação acima**; `python -m http.server` não executa o modelo.

## Preparar e interpretar

1. Escolher **observar um cenário** ou **comparar dois**. A comparação usa as
   mesmas sementes e horizonte em A/B.
2. Selecionar o roteiro de partida e ler pergunta, orientação e limites. Em
   **Base conceitual e hipótese**, consultar a obra, seu tipo de evidência,
   aplicações publicadas, hipótese observável, resultados contrários e limites.
   Links externos só são abertos por ação da pessoa.
3. Opcionalmente editar parâmetros básicos/avançados de cada condição.
   **Restaurar valores do roteiro** recupera sua configuração original.
4. Conferir os valores e diferenças, escolher repetições, semente inicial e
   horizonte e executar. Há progresso e cancelamento. Editar invalida a
   preparação anterior; resultados antigos não passam a representar o rascunho.

**Preparar comparação deste roteiro** aplica o desenho indicado em A/B para
conferência; não inicia a simulação. O botão substitui os dois rascunhos e a
pessoa pode editá-los ou restaurá-los. Explicações se referem ao roteiro
original; personalizações podem mudar o alcance da hipótese.

Na exploração, reproduzir, pausar, avançar, retroceder ou arrastar a linha do
tempo. Rede, eventos, curvas e conclusão usam o mesmo período visível. Rede
e eventos mostram a primeira semente; curvas mostram média das sementes
executadas. A faixa p10–p90 aparece com N >= 2 e não é intervalo de confiança.
Reproduzir percorre registros; não calcula subetapas internas nem muda o passado.

A definição de parceria produtiva usa o limiar efetivamente configurado.
Se A e B tiverem limiares diferentes, as duas contagens são identificadas
separadamente e o delta desse indicador fica indisponível: mudar a definição
da medida não implica mudar a rede. Os demais indicadores continuam
comparáveis nas mesmas sementes. A figura leva identificação de simulação,
período, sementes, N, cenários e definição da medida dentro de sua própria
área. Mensagens de falha de conexão orientam verificar o servidor e tentar
novamente, mantendo os parâmetros editados.

Os seis resultados são população ativa, parcerias produtivas, conhecimento
médio, inovação acumulada, capital e congestionamento. São unidades do modelo;
capital não é convertido em R$. A origem de atributos agregados não transforma
as trajetórias em observações empíricas. Hipóteses H1–H6 e experimentos E1–E7
continuam definidos em seus documentos científicos.

## Limites operacionais desta interface

| Recurso | Limite |
| --- | --- |
| Sementes por condição | 1–8; a UI oferece 1, 4 ou 8 |
| Semente inicial | 0–1.000.000; repetições consecutivas |
| Horizonte | API 1–80; UI oferece 20, 40, 60 ou 80 |
| População inicial | Até 100 por tipo e 150 no total |
| Entradas potenciais | Até 5 por período |
| Tentativas de parceria | Até 20 por startup/período |
| Relações ativas | Execução interrompida acima de 3.000 |
| Setores | Até 12 nomes de até 40 caracteres |
| Valores numéricos | Finitos e módulo <= 1 bilhão, além da validação canônica |
| Trabalhos | Um ativo; até quatro mantidos em memória |
| Dados pessoais | Importação de microdados não oferecida |

São limites do adaptador interativo, não novos limites ou mecanismos do modelo.
O cancelamento é cooperativo entre períodos; nenhum resultado parcial é
aplicado. Trabalhos e rascunhos não têm persistência garantida após reiniciar
o servidor ou recarregar a página: exportar a evidência desejada.

## API local

Base `http://127.0.0.1:8777`; JSON UTF-8, sem serviço externo ou LLM em runtime.

| Método/rota | Função |
| --- | --- |
| `GET /` ou `/index.html` | HTML gerado |
| `GET /api/investigation/health` | Disponibilidade, schema 3, limites e proveniência do servidor |
| `POST /api/investigation/run` | Valida e inicia; retorna HTTP 202 e `job_id` |
| `GET /api/investigation/jobs/{id}` | Progresso, estado e resultado quando completo |
| `POST /api/investigation/cancel` | Solicita cancelamento por `job_id` |

Corpo mínimo de uma execução:

```json
{
  "mode": "observe",
  "n_seeds": 1,
  "base_seed": 42,
  "periods": 20,
  "conditions": {
    "A": {"name": "Capacidade personalizada", "params": {"infrastructure_capacity": 13}}
  }
}
```

Para `mode: "compare"`, fornecer exatamente A e B. Parâmetros ausentes na API
recebem os padrões canônicos; a UI envia a configuração efetiva completa.
Campos de política usam prefixo `policy__`. Estados: `running`, `done`,
`cancelled` e `error`; erros e validações têm mensagem em português. O corpo
fica limitado a 65.536 bytes; `Origin`, quando presente, deve coincidir com o
servidor. Respostas JSON podem usar gzip conforme `Accept-Encoding`.

## Evidência, reprodução e exportação

- JSON de exportação: schema `investigation-workbench-3`, modo, condições,
  parâmetros completos, sementes, período visível, horizonte de reprodução,
  históricos e eventos até o cursor, interpretação e limitações. O campo
  aditivo `measurement` registra definição, limiares e comparabilidade do
  indicador selecionado.
- Cada condição identifica exemplo registrado ou execução nova; conserva
  proveniência, roteiro-base, dossiê, fontes e indicação de personalização.
- O servidor registra versão instalada, ambiente, commit, árvore com
  alterações e hashes dos fontes ao iniciar. O gerador faz seu próprio registro
  ao construir o HTML. Reconstruir e reiniciar após mudar fontes ou commit.
- CSV schema `investigation-trajectories-2`: uma linha por condição/semente/
  período, **incluindo p0**, até o cursor. São `N × (p + 1)` linhas por
  condição; p0 não gera mais um arquivo só com cabeçalho. As seis métricas
  conservam precisão de máquina e ponto decimal. Cada linha leva roteiro,
  origem, versão, commit, árvore alterada, `config_json` (com a semente da
  própria linha), `provenance_json` (ambiente e hashes) e `measurement_json`.
  Aspas, vírgulas e quebras de linha são escapadas como campos CSV. A repetição
  dos metadados aumenta o tamanho do arquivo, mas permite compartilhar o CSV
  sozinho sem perder a configuração. O JSON continua levando o dossiê e as
  referências; os arquivos não embutem o código-fonte, que deve ser preservado
  na versão e nos hashes registrados.
- Rede completa não integra o JSON exportado. Pode ser reconstruída com os
  parâmetros, sementes, horizonte e fontes registrados; não há importação
  automática do JSON na interface nesta versão.

## Arquivos e validação

| Arquivo | Responsabilidade |
| --- | --- |
| `src/technology_park_abm/investigation.py` | Validação interativa e registro semeado de métricas, eventos e quadros |
| `scripts/build_investigation_prototype.py` | Exemplos e HTML independente |
| `scripts/serve_investigation_prototype.py` | HTTP local e trabalhos em memória |
| `docs/prototypes/investigation*.html`, `*.js` | Fontes da interface embutidas pelo gerador |
| `docs/prototypes/investigation-scenarios.json` | Seleção, referências, hipóteses e contrastes |
| `tests/test_investigation_prototype.py` | Reprodução, execução, jornada, definições comparáveis, CSV reprodutível, recuperação de rede, fontes, exportação e a11y |

```powershell
.venv/Scripts/python.exe -m playwright install chromium
.venv/Scripts/python.exe scripts/run_checks.py
.venv/Scripts/python.exe scripts/check_gates.py
```

Registro técnico: [`verification-investigation-2026-10-24.md`](verification-investigation-2026-10-24.md).
Plano: [`investigation-prototype-plan.md`](investigation-prototype-plan.md).
Histórico das quatro iterações: [`investigation-prototype-review.md`](investigation-prototype-review.md).
Esta alternativa tem operação e aceitação locais. O deploy do dashboard
original em 8765 está em [`deploy.md`](deploy.md) e não pública esta prévia.

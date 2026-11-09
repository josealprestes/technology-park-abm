# Seleção de roteiros: literatura, mecanismos e direção de observação

Revisão focal em 24/10/2026. Aplicação: etapa 02, item 2, da prévia de
investigação. Pergunta: os roteiros ajudam a estudar como heterogeneidade,
redes, conhecimento, governança e congestionamento alteram o desempenho?

## Resultado da revisão

A seleção anterior continha mecanismos pertinentes, mas não era suficiente
para chamar seus roteiros de testes das teorias citadas. Faltava um contraste
direto de tamanho para H1; alguns títulos prometiam fenômenos que as regras
não implementam. A recomendação é uma seleção por mecanismos e perguntas,
com comparações explícitas, em vez de uma lista de narrativas com desfechos
favoráveis presumidos. Essa recomendação é uma inferência de projeto desta
revisão, não um ranking publicado dos melhores cenários.

A [revisão de Albahari et al. (2023)](https://doi.org/10.1007/s10961-022-09949-7)
e o [estudo brasileiro de Bolliger et al. (2025)](https://doi.org/10.1007/s10961-024-10143-0)
reforçam a importância da heterogeneidade entre firmas, parques e contextos.
Não há base para tratar um parque representativo ou um efeito médio como
resposta universal. O primeiro trabalho foi consultado integralmente; do
segundo foram consultados resumo, metadados e notas públicas.

## Método e alcance

Busca focal, sem pretensão de revisão sistemática, meta-análise ou exaustividade.
Foram cruzadas quatro frentes: ABM de redes e políticas de inovação; estudos
empíricos e revisões de parques; economia da aglomeração e inovação; referências
e direção didática da disciplina IA006J. As buscas incluíram combinações de
`agent-based innovation networks`, `science technology parks heterogeneous
effects`, `anchor tenant`, `related variety`, `university knowledge links`,
`network resilience`, `agglomeration economies`, `mission-oriented policy`
e suas variantes, com busca adicional por trabalhos de 2024–2026.

Priorizaram-se páginas de periódicos, artigos dos autores e repositórios
institucionais. Foram excluídos como fundamento substantivo resultados de
busca genéricos e resumos de terceiros quando havia fonte primária acessível.
O nível de acesso é declarado por obra: ler um resumo não é ler o artigo
integral. O catálogo registra 19 referências; também foram consultados outros
registros durante a triagem, sem convertê-los automaticamente em fundamentos.

Confrontou-se cada proposta com `DEMO_PLAYBOOKS`, `ModelConfig`, E1–E7 e as
métricas disponíveis na prévia. Uma hipótese só é proposta para observação
quando existe mecanismo executável; limitações de métricas, desenho e escala
ficam explícitas. Nenhuma busca ou explicação equivale a nova confirmação de
H1–H6, calibração empírica ou resultado de experimento.

## Decisões de seleção

| Roteiro na prévia | Decisão e adequação | Contraste oferecido | Limite principal |
| --- | --- | --- | --- |
| Massa crítica e tamanho do parque | Acrescentar; aproxima a jornada de H1 | 8 vs. 16 startups; entradas 0, capacidade 64 | Totais crescem com N; dois tamanhos não estimam escala nem contribuição marginal |
| Âncora ativa e difusão de conhecimento | Manter como mecanismo central, H3 | Mesma âncora ativa vs. passiva | Regra de difusão não é validada por sua própria consequência |
| Diversidade e complementaridade setorial | Manter e precisar a pergunta, H2 parcial | Mesma composição; complementaridade entre setores 0,8 vs. 0 | Não varia diversidade; H2 completa requer E2 |
| Capacidade, custos e congestionamento | Manter, H5 parcial | Capacidade 8 vs. 24, demais condições comuns | Limiar é imposto; custo da expansão não está modelado |
| Instrumentos de conexão e apoio | Renomear; investigar H4 sem presumir vencedor | Matchmaking 0,5 vs. 0, infraestrutura compartilhada fixa | Sem missão explícita, orçamento comparável ou custo-benefício; consultar E4 |
| Choque central e trajetória de recuperação | Manter como preparação para H6 | Choque p20 vs. sem choque | Não varia distribuição da rede; H6 exige E7 e métricas de recuperação |
| Universidade e relações com empresas | Renomear Hélice tríplice; complementar | Universidades ativas vs. passivas | Governo não é uma esfera institucional coevolutiva modelada |
| Financiamento e restrições de recursos | Renomear Onda de investimento; complementar | Fundo 100 vs. 0, mesmos investidores | Não há ciclos de revolução tecnológica, bolhas ou contratos de VC |
| Entradas, saídas e renovação | Renomear Destruição criativa; complementar | Entradas potenciais 2 vs. 0 | Não representa substituição tecnológica de incumbentes; não é teste de H1 |
| Heterogeneidade com atributos agregados | Renomear Dados reais; sensibilidade | Inicialização por agregados vs. sintética | Dados de entrada não validam processos/saídas; não isola cada atributo |
| Capacidade ampliada | Preservar como variação | Capacidade 24 vs. 8 | É outro ponto da mesma família, não outro mecanismo |

Os nove conjuntos originais de parâmetros foram preservados. Os nomes e
enquadramentos revistos pertencem à prévia; `original_name` mantém a ligação
com os roteiros da release. O novo roteiro de massa crítica é opt-in, sem
alterar padrões, mecanismos, goldens ou os experimentos registrados.
O par 8/16 e a capacidade 64 são escolhas didáticas desta implementação,
não estimativas extraídas da literatura. E1 usa sua própria grade 2/8/16.

## O que a literatura permite transferir

[Duranton e Puga (2004)](https://www.nber.org/papers/w9931) organizam os
benefícios da aglomeração em compartilhamento, encontros e aprendizagem.
Essa decomposição orienta quais regras e resultados inspecionar. A literatura
urbana não fornece diretamente a fórmula de congestionamento do parque.

O [ABM de Gilbert, Pyka e Ahrweiler (2001)](https://www.jasss.org/4/3/8.html)
é um antecedente para representar conhecimento heterogêneo, colaboração e
renovação. Seus casos de telecomunicações e biotecnologia ilustram aplicação
setorial; a prévia não reproduz o SKIN. A avaliação de políticas da família
SKIN aparece também no [registro institucional REF/Surrey](https://impact.ref.ac.uk/casestudies/CaseStudy.aspx?Id=40575),
consultado como evidência de uso publicado, sem alegar que este projeto foi
utilizado por aquelas instituições.

[Agrawal e Cockburn (2003)](https://doi.org/10.1016/S0167-7187(03)00081-X)
oferecem uma referência mais próxima da função da âncora que uma sequência
genérica de autores sobre crescimento. O canal universitário recebe um caso
específico: [Díez-Vial e Montoro-Sánchez (2016), Madrid Science Park](https://doi.org/10.1016/j.technovation.2015.09.001).
Esses dois vínculos foram avaliados a partir dos resumos e registros dos
periódicos; não foram importados coeficientes empíricos para o simulador.

Corrigiu-se a referência de variedade relacionada para
[Frenken, van Oort e Verburg (2007)](https://doi.org/10.1080/00343400601120296).
Seu contexto é o de regiões neerlandesas, não uma demonstração de que qualquer
diversidade favorece inovação. [Feng et al. (2026)](https://www.nature.com/articles/s41599-026-08025-x)
oferecem um ABM recente de cooperação interdisciplinar universitária; seu
contexto e seu resultado de número de áreas não são transferidos ao parque.

[Crespo, Suire e Vicente (2014)](https://academic.oup.com/joeg/article-abstract/14/1/199/1046260)
aproximam resiliência de propriedades estruturais da rede. Seu resumo foi
consultado; a versão integral institucional não ficou disponível. Isso
justifica restringir a explicação e encaminhar H6 ao desenho próprio de E7.

[Kerr, Nanda e Rhodes-Kropf (2014)](https://www.aeaweb.org/articles?id=10.1257/jep.28.3.25)
ajudam a formular financiamento como condição para experimentar, sem exigir
um ciclo financeiro não implementado. Para políticas, a aplicação ABM de
[Müller, Kudic e Pyka (2017)](https://doi.org/10.14512/tatup.26.3.51)
é particularmente útil: intervenções podem ter efeitos adversos conforme a
rede. [Mazzucato (2018)](https://doi.org/10.1093/icc/dty034) ajuda a delimitar
o que faltaria para chamar o cenário de missão, em vez de apoio à conexão.

## Contribuição do material de IA006J

Consulta somente leitura em `D:/Projetos/Unicamp/IA006J`, a partir das pastas
canônicas `Referências da Aula N`. Foram extraídos 12 PDFs das Aulas 4, 7,
8, 9 e 10 para localização de passagens; a consulta foi focal, não leitura
integral de todo o acervo. Inventário de arquivos, páginas e SHA-256 em
`outputs/ia006j-research/receipt.json`. Nenhuma resposta anterior da disciplina
foi usada como autoridade científica e nenhum notebook foi executado.

- Aula 4: Rand e Rust e o material de laboratórios computacionais de
  Tesfatsion orientam a separação entre desenho, verificação, validação e
  avaliação de alternativas. O artigo de [Rand e Rust (2011)](https://doi.org/10.1016/j.ijresmar.2011.04.002)
  é a referência bibliográfica; não é um estudo empírico de parques.
- Aula 7: `Aula07_02_redes_generativas.pdf`, pp. 2–4, orienta a leitura das
  regras que formam a rede, em vez de inferir mecanismo apenas pela figura.
- Aula 8: o estudo de [Bettencourt et al. (2007)](https://doi.org/10.1073/pnas.0610172104)
  motiva distinguir evolução temporal de relação entre tamanho e resultado.
  `261029_Aula08_01_Cidades_Bettencourt_V1.pdf`, pp. 2 e 5, foi consultado
  pelo conteúdo, sem inferir data de aula a partir do nome do arquivo.
- Aula 9: foram lidos os textos originais de
  [Arthur (1990)](https://sites.santafe.edu/~wbarthur/Papers/SciAm_Article.pdf)
  e [Arthur (2021)](https://doi.org/10.1038/s42254-020-00273-3) presentes no
  acervo. Realimentação, história e adaptação orientam as perguntas; o modelo
  atual não implementa aprendizagem de estratégias ou lock-in tecnológico.
- Aula 10: `Aula_10_03_IA006_2026_2S_tirar_proveito_complexidade.pdf`, pp. 6–8,
  orienta a passagem de observação para comparação de alternativas. O modelo
  ainda não tem uma busca adaptativa automática por estratégias. O material
  de sustentabilidade ajuda a identificar uma lacuna: inovação e capital
  não medem impacto ambiental, inclusão ou cumprimento de ODS.

Slides orientam o direcionamento didático e são identificados como material
consultado; as obras dos autores constituem as referências bibliográficas.

## Lacunas que não se resolvem com títulos novos

1. Redes externas e relações entre parques. A aplicação empírica ABM de
   [Neuländtner et al. (2025)](https://doi.org/10.1007/s00168-025-01402-5)
   e o estudo de [Ancona e Ceci (2026)](https://doi.org/10.1007/s10961-025-10308-5)
   mostram direções relevantes, em escalas diferentes. Não há atores externos
   ou adesão de parques a redes internacionais no modelo atual.
2. Capacidade de absorção, memória e adaptação de estratégias. Os atuais
   estoques e coeficientes não bastam para afirmar que esses mecanismos
   estão implementados ou calibrados.
3. H6: redes distribuídas versus centralizadas e recuperação funcional. O
   roteiro de choque serve à observação; E7 mantém o papel de teste estrutural.
4. Sustentabilidade e missões: requerem objetivos e indicadores próprios,
   custos comparáveis e processos de governança, não apenas inovação agregada.
5. Transferência empírica: são necessárias observações de redes e firmas,
   calibração e validação independente antes de recomendar políticas reais.

Essas frentes ficam documentadas como direção futura; não foram introduzidas
novas regras científicas nesta revisão.

## Entrega na interface e verificação

O catálogo versionado `docs/prototypes/investigation-scenarios.json` contém
fontes, nível de acesso, aplicações, hipóteses, comportamentos observáveis,
evidência contrária, limites e contrastes. Alimenta os cartões, o catálogo,
a bibliografia e o JSON exportado. Hashes do catálogo entram na proveniência.

A comparação sugerida prepara duas configurações revisáveis e não inicia o
motor. A pessoa pode editar ou descartar o par. A execução continua opcional,
semeada e marcada como simulação. Textos referem-se ao roteiro de partida;
personalizações podem mudar o alcance da hipótese.

Testes verificam a preservação dos nove parâmetros originais, execução real
dos contrastes, ausência de execução ao preparar, exportação das fontes,
reprodução, acessibilidade e reflow. O fechamento técnico desta revisão é
registrado em `docs/investigation-prototype-review.md`; entendimento humano,
adequação empírica e confirmação científica não são certificados pelos testes.

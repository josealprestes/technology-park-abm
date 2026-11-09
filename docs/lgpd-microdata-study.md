# Estudo de base legal: microdados de mercado de trabalho (LGPD/ANPD)

Status: concluído em 2026-10-22. Resultado: ADR 0012 (ingestão restrita a
agregados oficiais e registros públicos de pessoas jurídicas) e contratos
de dados schema 1.1 (`docs/data-contracts.md`).

Aviso: este é um estudo de engenharia de software, não um parecer jurídico.
Antes de qualquer mudança de escopo, consultar o encarregado de dados
(DPO) da instituição.

## 1. Questão

O plano de enriquecimento (`docs/agent-enrichment-plan.md`, E1-E4) prevê
inicializar atributos de agentes a partir de distribuições empíricas de
microdados de mercado de trabalho (RAIS, Novo CAGED). Este estudo avalia
se há base legal para ingerir esses microdados neste projeto e, se não,
quais fontes alternativas cobrem as mesmas necessidades de calibração.

## 2. Fatos sobre as fontes (verificados em 2026-10-22)

| Fonte | Forma de acesso | Granularidade | Observações |
| --- | --- | --- | --- |
| RAIS microdata (MTE/PDET) | TXT bulk via FTP (`ftp.mtps.gov.br/pdet/microdados/`); uso acadêmico mediante termo de responsabilidade | vínculo (trabalhador × estabelecimento), anual | registros em nível de trabalhador — dados pessoais |
| Novo CAGED microdata (MTE/PDET) | TXT bulk via FTP, mensal | movimentação (admissão/desligamento) em nível de trabalhador | registros em nível de trabalhador — dados pessoais |
| CAGED Estatístico (PAINEL/VÍNCULO) | acesso mediante solicitação e aprovação do MTE, com senha (`acesso.trabalho.gov.br`) | movimentação/vínculo | fonte autenticada — fora de escopo (ADR 0004) |
| IBGE SIDRA (API de agregados) | API pública (`apisidra.ibge.gov.br`, `servicodados.ibge.gov.br`) | agregados estatísticos oficiais | sem dados pessoais |
| INPI dados abertos | download bulk mediante registro | registros de depósitos com nomes de titulares/inventores | nomes de pessoas físicas — dados pessoais |
| dados.gov.br | portal; a API exige autenticação (Bearer) desde 2026 | catálogo de recursos | o portal bloqueia recursos com CPF ou dados sensíveis (LGPD) |
| World Bank Open Data | API pública | agregados país/ano | sem dados pessoais |
| CNPJ (Receita Federal, via BrasilAPI) | API pública | dados de pessoas jurídicas (registro público) | pessoas jurídicas não são titulares sob a LGPD (art. 5º, I: pessoa natural) |

Não existe API oficial aberta do MTE para agregados mensais do Novo
CAGED; as publicações agregadas são tabelas web (não estáveis para
ingestão automatizada) e os microdados são exclusivamente bulk via FTP.

## 3. Quadro normativo

- **LGPD (Lei nº 13.709/2018)**:
  - art. 5º, I: dado pessoal é o que permite identificar pessoa natural;
  - art. 6º: princípios — finalidade, adequação, necessidade
    (minimização), transparência;
  - art. 7º: hipóteses de tratamento; inciso IX (pesquisa), disciplinado
    pelo art. 10;
  - art. 11º: dados sensíveis; inciso II (pesquisa, com anonimização);
  - art. 12º: dado anonimizado (padrão de anonimização baseado em risco);
  - art. 41º: encarregado (DPO);
  - art. 46º: medidas de segurança;
  - art. 48º: comunicação de incidentes;
  - art. 52º: sanções administrativas.
- **Decreto nº 8.777/2016**: Política de Dados Abertos do Poder Executivo
  federal — base para a abertura de dados oficiais brasileiros.
- **ANPD**: Guia Orientativo sobre Tratamento de Dados Pessoais para o
  Poder Público; Guia de legítimo interesse (set/2022); Estudo técnico
  sobre anonimização de dados na LGPD (2024) — a anonimização é um
  processo baseado em risco e não garante anonimato absoluto; o art. 10,
  II, § 3º admite que a ANPD exija Relatório de Impacto à Proteção de
  Dados Pessoais (RIPD).
- **MTE/PDET**: termos de uso dos microdados RAIS/CAGED (FTP bulk) e
  acesso condicionado por aprovação para o CAGED Estatístico.

## 4. Análise

1. **Os microdados RAIS/CAGED são dados pessoais.** Registros em nível de
   trabalhador permitem identificar pessoas naturais (direta ou
   indiretamente). "Desidentificado" não é sinônimo de anonimizado: sob o
   estudo técnico da ANPD (2024), a anonimização é um processo baseado em
   risco, e a mera remoção de CPF não anonimiza (art. 12º c/c art. 5º, I).
2. **O tratamento para pesquisa exigiria base legal documentada.** A
   hipótese do art. 7º, IX (pesquisa), com o art. 11º, II para dados
   sensíveis, impõe minimização (art. 6º), segurança (art. 46º),
   encarregado (art. 41º) e, potencialmente, RIPD (art. 10, § 3º). Para um
   projeto de código aberto que versiona scripts e checksums, operar sobre
   microdados de trabalhadores introduz obrigações de governança
   desproporcionais ao benefício científico.
3. **O acesso é bulk e/ou autenticado.** RAIS/CAGED microdata são
   distribuídos como arquivos TXT volumosos via FTP (centenas de MB por
   ano); o CAGED Estatístico exige aprovação e senha. Fontes autenticadas
   já estão fora de escopo (ADR 0004).
4. **Agregados oficiais cobrem a mesma necessidade.** O modelo precisa
   de distribuições marginais e correlações (escolaridade, idade, salário,
   porte, sobrevivência de firmas), não de registros individuais. O SIDRA
   pública exatamente esses agregados (PNAD Contínua, CEMPRE, Demografia
   das Empresas) via API pública, sem dados pessoais, com checksums
   reproduzíveis.
5. **Minimização favorece agregados.** Pelo art. 6º (necessidade), se
   agregados atendem à finalidade de calibração, microdados são
   desnecessários.

## 5. Decisão (ADR 0012)

- Ingestão restrita a **agregados estatísticos oficiais** (SIDRA/IBGE,
  World Bank) e **registros públicos de pessoas jurídicas** (CNPJ).
- **Microdados de trabalhadores (RAIS, Novo CAGED, CAGED Estatístico)
  estão fora de escopo**, catalogados como `catalog-only` com
  `personal_data: "personal"` e a razão de fora de escopo registrada.
- O contrato de catálogo (schema 1.1) exige `legal_basis` e
  `personal_data` por fonte e **proíbe mecanicamente** o download de
  fontes com dados pessoais (`data_contracts.validate_catalog_entry`).
- Qualquer uso futuro de microdados exige novo ADR com base legal
  documentada (art. 7º/11º), RIPD, operador/encarregado definidos e
  retenção mínima.

## 6. Consequências

- O catálogo (`data/manifest.json`) migrou para schema 1.1 com os campos
  `legal_basis` e `personal_data` em todas as fontes.
- Cinco fontes SIDRA foram ingeridas com checksums reais
  (PNAD Contínua: educação e idade dos ocupados, rendimento por
  instrução; CEMPRE: pessoal ocupado e salário médio por seção CNAE;
  Demografia das Empresas: nascimentos e sobrevivência por seção CNAE).
- Retenção: apenas agregados, scripts e checksums são versionados; raw
  nunca entra no git (ADR 0004, política de dados do runner).
- Limitações: estudo de engenharia, não parecer jurídico; a
  interpretação da ANPD sobre anonimização e pesquisa evolui — revisar
  este estudo a cada ciclo de release.

## 7. Referências

- Lei nº 13.709/2018 (LGPD), arts. 5º, 6º, 7º, 10, 11, 12, 41, 46, 48, 52.
- Decreto nº 8.777/2016 (Política de Dados Abertos do Poder Executivo).
- ANPD, Guia Orientativo sobre Tratamento de Dados Pessoais para o Poder
  Público; Guia de legítimo interesse (2022); Estudo técnico sobre
  anonimização de dados na LGPD (2024). gov.br/anpd.
- MTE/PDET, Microdados RAIS e CAGED (FTP bulk) e Bases de Dados (CAGED
  Estatístico, mediante aprovação). gov.br/trabalho-e-emprego;
  acesso.trabalho.gov.br.
- IBGE, API SIDRA / API de agregados. apisidra.ibge.gov.br;
  servicodados.ibge.gov.br.

"""Shared configuration kernel for the investigation workbench.

Extracted verbatim from the former dashboard module (``dashboard.py``,
retired in v2.15.0): parameter specs and coercion, PT-BR error
translation, the canonical scenario catalog (``DEMO_PLAYBOOKS``), and
the deterministic map layout. The workbench (``investigation.py``, the
builder, and the 8777 server) is the only consumer.

``DEMO_PLAYBOOKS`` carries the numeric ``params`` that are the source of
truth for the nine canonical tours; ``docs/prototypes/investigation-
scenarios.json`` overlays names, dossiers, and contrasts but never
changes these numbers.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields, replace
from typing import Any

from .agents import PARTICIPATION_LEVELS
from .config import SHOCK_TYPES, ModelConfig, Policy
from .empirical import (
    CONNECTION_PROFILES,
    EMPIRICAL_MODES,
    SECTOR_PROFILE_NAMES,
)
from .model import TechnologyParkModel

REGIONS: tuple[dict[str, Any], ...] = (
    {
        "key": "anchor",
        "label": "Empresas-ancora",
        "x0": 0.10,
        "x1": 0.90,
        "y0": 0.86,
        "y1": 0.98,
    },
    {
        "key": "university",
        "label": "Universidade",
        "x0": 0.78,
        "x1": 0.98,
        "y0": 0.58,
        "y1": 0.72,
    },
    {
        "key": "investor",
        "label": "Investidores",
        "x0": 0.82,
        "x1": 0.98,
        "y0": 0.26,
        "y1": 0.52,
    },
    {
        "key": "worker",
        "label": "Trabalhadores",
        "x0": 0.10,
        "x1": 0.90,
        "y0": 0.02,
        "y1": 0.14,
    },
    {
        "key": "startup",
        "label": "Startups",
        "x0": 0.08,
        "x1": 0.72,
        "y0": 0.20,
        "y1": 0.64,
    },
)


GROUP_ORDER: tuple[str, ...] = (
    "Population",
    "Entry",
    "Partnerships",
    "Knowledge",
    "Finance",
    "Congestion",
    "Exits & Shocks",
    "Anchors & Reputation",
    "Policy",
    "Empirical",
    "Environment",
)


CHOICE_FIELDS: dict[str, tuple[str, ...]] = {
    "anchor_participation": PARTICIPATION_LEVELS,
    "university_participation": PARTICIPATION_LEVELS,
    "empirical_init": EMPIRICAL_MODES,
    "sector_profiles": SECTOR_PROFILE_NAMES,
    "connection_profile": CONNECTION_PROFILES,
}


TEXT_FIELDS: tuple[str, ...] = ("sectors", "microdata_path")


_PROBABILITY_FIELDS = frozenset(
    {
        "rnd_share",
        "market_access_gain",
        "knowledge_depreciation",
        "entry_base_probability",
        "partnership_base_probability",
        "partnership_dissolution_probability",
        "productive_tie_strength_threshold",
        "hiring_probability",
        "investment_probability",
        "investment_min_quality",
        "investor_burn_relief",
        "acquisition_probability",
        "acquisition_min_quality",
        "voluntary_exit_probability",
        "migration_probability",
        "reputation_update_rate",
        "same_sector_compatibility",
        "cross_sector_compatibility",
        "same_sector_complementarity",
        "cross_sector_complementarity",
    }
)


_FLOAT_OVERRIDES: dict[str, tuple[float, float, float]] = {
    "initial_capital": (0.0, 5000.0, 10.0),
    "investor_capital": (0.0, 5000.0, 10.0),
    "investment_amount": (0.0, 1000.0, 10.0),
    "policy__investment_fund": (0.0, 5000.0, 10.0),
    "congestion_cost_per_org": (0.0, 100.0, 0.1),
    "burn_rate": (0.0, 100.0, 0.1),
    "labor_cost_per_worker": (0.0, 100.0, 0.1),
}


_ERROR_PHRASES: tuple[tuple[str, str], ...] = (
    ("n must be between", "o número de períodos precisa estar entre"),
    ("must be non-negative", "precisa ser não-negativo"),
    ("must be an integer or None", "precisa ser um número inteiro (ou nada)"),
    ("must be at least 1", "precisa ser no mínimo 1"),
    ("must be in [0, 1]", "precisa estar entre 0 e 1"),
    ("must be a JSON object", "precisa ser um objeto JSON"),
    ("must be one of", "precisa ser um de"),
    ("at least one sector is required", "pelo menos um setor é obrigatório"),
    ("must be between", "precisa estar entre"),
    ("must be", "precisa ser"),
)


def _translate_error(message: str) -> str:
    """C5 (auditoria client-adversarial, M11): mensagens de validação saem do
    modelo em snake_case/inglês; o usuário vê rótulos PT-BR. Traduz a
    MENSAGEM na borda HTTP — a validação em si fica intacta."""
    out = message.replace("policy.", "policy__")
    for name, label in sorted(_LABELS.items(), key=lambda kv: -len(kv[0])):
        if name in out:
            out = out.replace(name, label)
    for english, portuguese in _ERROR_PHRASES:
        out = out.replace(english, portuguese)
    return out


_LABELS: dict[str, str] = {
    "seed": "Semente aleatória",
    "n_startups": "Startups iniciais",
    "n_anchor_firms": "Empresas-âncora",
    "n_universities": "Universidades / ICTs",
    "n_investors": "Investidores",
    "n_workers": "Trabalhadores qualificados",
    "initial_capital": "Capital inicial por startup",
    "burn_rate": "Custo operacional por período",
    "sectors": "Setores (separados por vírgula)",
    "infrastructure_capacity": "Capacidade da infraestrutura",
    "funding_conditions": "Funding disponível",
    "labor_market_slack": "Oferta de profissionais",
    "same_sector_compatibility": "Compatibilidade (mesmo setor)",
    "cross_sector_compatibility": "Compatibilidade (entre setores)",
    "same_sector_complementarity": "Complementaridade (mesmo setor)",
    "cross_sector_complementarity": "Complementaridade (entre setores)",
    "entry_potential_per_period": "Novas startups por período",
    "entry_base_probability": "Chance base de entrada",
    "entry_reputation_weight": "Atração por reputação",
    "entry_funding_weight": "Atração por funding",
    "entry_infrastructure_weight": "Atração por infraestrutura",
    "entry_opportunity_weight": "Atração por oportunidade",
    "entry_cost_weight": "Efeito do custo",
    "partnership_attempts_per_startup": "Tentativas de parceria",
    "partnership_base_probability": "Chance base de parceria",
    "partnership_compatibility_weight": "Efeito da compatibilidade",
    "partnership_complementarity_weight": "Efeito da complementaridade",
    "partnership_reputation_weight": "Efeito da reputação",
    "partnership_cost_weight": "Efeito do congestionamento",
    "partnership_dissolution_probability": "Chance de desfazer parceria",
    "productive_tie_strength_threshold": "Limiar de parceria produtiva",
    "rnd_share": "Esforço em P&D",
    "knowledge_rnd_gain": "Ganho de P&D",
    "market_access_gain": "Conquista de mercado",
    "knowledge_spillover_rate": "Difusão de conhecimento",
    "knowledge_depreciation": "Depreciação do conhecimento",
    "innovation_event_threshold": "Limiar de inovação",
    "revenue_per_access": "Receita por acesso",
    "labor_cost_per_worker": "Custo por trabalhador",
    "max_team_size": "Equipe máxima",
    "hiring_probability": "Chance de contratar",
    "hiring_knowledge_gain": "Conhecimento ao contratar",
    "investment_probability": "Chance de aporte",
    "investment_amount": "Valor do aporte",
    "investment_min_quality": "Qualidade mínima para aporte",
    "investor_capital": "Capital do investidor",
    "investor_burn_relief": "Alívio de custo do investidor",
    "congestion_cost_per_org": "Custo de congestionamento",
    "acquisition_probability": "Chance de aquisição",
    "acquisition_min_quality": "Qualidade mínima para aquisição",
    "voluntary_exit_probability": "Chance de saída voluntária",
    "migration_probability": "Chance de migração",
    "shock_period": "Período do choque",
    "shock_type": "Tipo de choque",
    "shock_nodes": "Empresas atingidas pelo choque",
    "anchor_participation": "Participação da âncora",
    "anchor_initial_knowledge": "Conhecimento da âncora",
    "reputation_update_rate": "Atualização da reputação",
    "empirical_init": "Inicialização empírica",
    "microdata_path": "Arquivo de microdados (CSV)",
    "sector_profiles": "Perfis setoriais",
    "connection_profile": "Perfil de conexões",
    "university_participation": "Participação da universidade",
    "policy__entry_subsidy": "Subsídio à entrada",
    "policy__rnd_subsidy": "Subsídio a P&D",
    "policy__shared_infrastructure": "Infraestrutura compartilhada",
    "policy__matchmaking": "Programa de matchmaking",
    "policy__talent_program": "Programa de talentos",
    "policy__investment_fund": "Fundo de investimento",
}


_DESCRIPTIONS: dict[str, str] = {
    "seed": (
        "Número que garante que a simulação seja reproduzível: "
        "mesma semente, mesmo resultado."
    ),
    "n_startups": "Quantas startups começam no parque.",
    "n_anchor_firms": (
        "Grandes empresas estabelecidas. Só interagem se a participação for ativa."
    ),
    "n_universities": "Instituições de pesquisa presentes no parque.",
    "n_investors": "Investidores disponíveis para aportar capital.",
    "n_workers": "Profissionais qualificados disponíveis para contratação.",
    "initial_capital": (
        "Dinheiro que cada startup tem ao entrar (unidades monetárias)."
    ),
    "burn_rate": "Quanto cada startup gasta por período só para operar.",
    "sectors": (
        "Lista de setores separados por vírgula. Organizações do mesmo setor "
        "cooperam mais facilmente."
    ),
    "infrastructure_capacity": (
        "Quantas organizações o parque suporta sem congestionamento."
    ),
    "funding_conditions": "Facilidade de captar recursos na região, de 0 a 1.",
    "labor_market_slack": "Disponibilidade de profissionais na região, de 0 a 1.",
    "same_sector_compatibility": (
        "Facilidade de cooperação entre organizações do mesmo setor, de 0 a 1."
    ),
    "cross_sector_compatibility": (
        "Facilidade de cooperação entre setores diferentes, de 0 a 1."
    ),
    "same_sector_complementarity": (
        "Potencial de aprendizado entre pares do mesmo setor, de 0 a 1."
    ),
    "cross_sector_complementarity": (
        "Potencial de aprendizado entre setores diferentes, de 0 a 1."
    ),
    "entry_potential_per_period": (
        "Máximo de novas startups que podem surgir a cada período."
    ),
    "entry_base_probability": "Probabilidade base de uma candidata entrar, de 0 a 1.",
    "entry_reputation_weight": "Quanto a reputação do parque atrai novas startups.",
    "entry_funding_weight": "Quanto o funding disponível atrai novas startups.",
    "entry_infrastructure_weight": (
        "Quanto a infraestrutura livre atrai novas startups."
    ),
    "entry_opportunity_weight": (
        "Quanto o conhecimento médio do parque atrai novas startups."
    ),
    "entry_cost_weight": "Quanto o custo operacional afasta novas startups.",
    "partnership_attempts_per_startup": (
        "Quantas vezes cada startup procura parceiras por período."
    ),
    "partnership_base_probability": (
        "Probabilidade base de firmar uma parceria, de 0 a 1."
    ),
    "partnership_compatibility_weight": (
        "Quanto a compatibilidade entre setores aumenta a chance de parceria."
    ),
    "partnership_complementarity_weight": (
        "Quanto a complementaridade entre setores aumenta a chance de parceria."
    ),
    "partnership_reputation_weight": (
        "Efeito da reputação das organizações na formação de parcerias."
    ),
    "partnership_cost_weight": (
        "Quanto o congestionamento reduz a chance de parceria."
    ),
    "partnership_dissolution_probability": (
        "Probabilidade de cada parceria terminar a cada período, de 0 a 1."
    ),
    "productive_tie_strength_threshold": (
        "Força mínima para uma parceria contar como produtiva, de 0 a 1."
    ),
    "rnd_share": (
        "Fração do esforço dedicada a pesquisa e desenvolvimento "
        "(o restante vai para mercado), de 0 a 1."
    ),
    "knowledge_rnd_gain": "Conhecimento gerado por unidade de esforço em P&D.",
    "market_access_gain": (
        "Velocidade com que a startup conquista clientes, de 0 a 1."
    ),
    "knowledge_spillover_rate": ("Quanto conhecimento flui pelas parcerias, de 0 a 1."),
    "knowledge_depreciation": (
        "Fração do conhecimento que se torna obsoleta por período, de 0 a 1."
    ),
    "innovation_event_threshold": (
        "Ganho mínimo de conhecimento no período para contar uma inovação."
    ),
    "revenue_per_access": (
        "Receita gerada por qualidade tecnológica multiplicada pelo acesso a clientes."
    ),
    "labor_cost_per_worker": "Custo de cada trabalhador contratado por período.",
    "max_team_size": "Limite de trabalhadores por startup.",
    "hiring_probability": (
        "Probabilidade de uma startup contratar por período, de 0 a 1."
    ),
    "hiring_knowledge_gain": "Conhecimento trazido por cada contratação.",
    "investment_probability": (
        "Probabilidade de um investidor aportar em uma startup, de 0 a 1."
    ),
    "investment_amount": "Capital transferido em cada aporte.",
    "investment_min_quality": (
        "Qualidade tecnológica mínima exigida pelo investidor, de 0 a 1."
    ),
    "investor_capital": "Quanto cada investidor tem disponível para aportar.",
    "investor_burn_relief": (
        "Fração do custo operacional aliviada para startups com aporte, de 0 a 1."
    ),
    "congestion_cost_per_org": (
        "Custo extra pago por cada organização acima da capacidade."
    ),
    "acquisition_probability": (
        "Probabilidade de uma startup ser adquirida por período, de 0 a 1."
    ),
    "acquisition_min_quality": (
        "Qualidade tecnológica mínima para interessar uma âncora, de 0 a 1."
    ),
    "voluntary_exit_probability": (
        "Probabilidade de uma startup sair por decisão própria, de 0 a 1."
    ),
    "migration_probability": (
        "Probabilidade de uma startup deixar o parque, de 0 a 1."
    ),
    "shock_period": (
        "Período em que um choque externo ocorre. Vazio significa sem choque."
    ),
    "shock_type": (
        "central_firm derruba a startup mais conectada; funding corta os investidores."
    ),
    "shock_nodes": (
        "Quantas empresas centrais o choque derruba, por grau de parceria."
    ),
    "anchor_participation": (
        "passive: a âncora não interage; active: forma parcerias e difunde "
        "conhecimento."
    ),
    "anchor_initial_knowledge": "Estoque de conhecimento das empresas-âncora.",
    "reputation_update_rate": (
        "Quão rápido a reputação do parque reage aos resultados, de 0 a 1."
    ),
    "empirical_init": (
        "none: atributos padrão; aggregates: distribuições públicas "
        "(PNAD/RAIS/CAGED); microdata: CSV de microdados."
    ),
    "microdata_path": (
        "Caminho de um CSV com colunas education, age, wage e skill "
        "(usado no modo microdata)."
    ),
    "sector_profiles": (
        "none: probabilidades uniformes; brazil_tech: multiplicadores "
        "setoriais de entrada, saída e contratação."
    ),
    "connection_profile": (
        "baseline: conexões padrão; empirical: bônus âncora-startup e "
        "escolha por qualidade e habilidade."
    ),
    "university_participation": (
        "passive: a universidade não interage; active: forma parcerias e "
        "difunde conhecimento."
    ),
    "policy__entry_subsidy": "Aumenta o atrativo de entrar no parque, de 0 a 1.",
    "policy__rnd_subsidy": ("Multiplica o ganho de conhecimento em P&D, de 0 a 1."),
    "policy__shared_infrastructure": (
        "Aumenta a capacidade efetiva da infraestrutura, de 0 a 1."
    ),
    "policy__matchmaking": "Aumenta a chance de parcerias, de 0 a 1.",
    "policy__talent_program": (
        "Multiplica o conhecimento trazido por contratações, de 0 a 1."
    ),
    "policy__investment_fund": "Capital extra adicionado a cada investidor.",
}


_SIMPLE_FIELDS = frozenset(
    {
        "seed",
        "n_startups",
        "n_anchor_firms",
        "anchor_participation",
        "initial_capital",
        "burn_rate",
        "infrastructure_capacity",
        "entry_potential_per_period",
        "partnership_attempts_per_startup",
        "rnd_share",
        "knowledge_spillover_rate",
        "congestion_cost_per_org",
        "voluntary_exit_probability",
        "sectors",
    }
)


DEMO_PLAYBOOKS: tuple[dict[str, Any], ...] = (
    {
        "name": "Destruição criativa",
        "category": "Demonstração",
        "description": "Entrada e saída de empresas ao longo do tempo.",
        "goal": (
            "Ver o parque renovar a própria população: empresas entram, "
            "crescem e saem, e o total oscila em torno de um nível."
        ),
        "steps": (
            "Clique em Rodar até o período 80 (use velocidade 4x para ir mais rápido).",
            "No gráfico População e parcerias, observe a linha de startups "
            "ativas subir e cair.",
            "Abra a tabela de dados e compare períodos: as entradas "
            "(marcadores vermelhos) e as saídas não acontecem no mesmo "
            "período.",
        ),
        "watch_for": (
            "A população oscila sem zerar: cada onda de saída é seguida de "
            "novas entradas — o parque se renova continuamente."
        ),
        "params": {},
        "phenomenon": "Renovação da população por entrada e saída",
        "reference": "Schumpeter (1942), Capitalismo, Socialismo e Democracia",
        "hypothesis": "H1",
    },
    {
        "name": "Âncora e spillovers",
        "category": "Demonstração",
        "description": "Uma empresa-âncora ativa difundindo conhecimento pela rede.",
        "goal": "Mostrar que a âncora só gera spillovers quando participa da rede.",
        "steps": (
            "Clique em Rodar até o período 40.",
            "Clique na âncora A1 no mapa (ou escolha na lista Inspecionar) "
            "e veja as relações destacadas.",
            "No gráfico Conhecimento e inovação, acompanhe o conhecimento "
            "total subir com a difusão.",
            "Para comparar, mude 'Participação da âncora' para 'passiva' "
            "em Calibrar e rode de novo com a mesma semente.",
        ),
        "watch_for": (
            "A âncora acumula parcerias (linhas verdes) e o conhecimento das "
            "startups conectadas cresce mais que o das isoladas."
        ),
        "params": {
            "n_anchor_firms": 1,
            "anchor_participation": "active",
            "anchor_initial_knowledge": 8.0,
        },
        "phenomenon": "Spillovers de conhecimento da empresa-âncora",
        "reference": (
            "Marshall (1890); Arrow (1962); Romer (1986); Audretsch & Feldman (1996)"
        ),
        "hypothesis": "H3",
    },
    {
        "name": "Hélice tríplice",
        "category": "Demonstração",
        "description": "Universidade ativa e canal universidade-indústria.",
        "goal": (
            "Ver a universidade formar parcerias e trocar conhecimento "
            "com as empresas do parque."
        ),
        "steps": (
            "Clique em Rodar até o período 60.",
            "Na legenda, oculte startups e trabalhadores para ver só "
            "universidades e âncoras.",
            "Clique na universidade U1 e veja as relações destacadas no mapa.",
        ),
        "watch_for": (
            "A universidade aparece conectada às empresas; o conhecimento "
            "médio sobe com o canal universidade-indústria."
        ),
        "params": {
            "empirical_init": "aggregates",
            "university_participation": "active",
            "n_universities": 2,
            "entry_potential_per_period": 1,
        },
        "phenomenon": "Interação universidade-indústria (hélice tríplice)",
        "reference": "Etzkowitz & Leydesdorff (1995), The Triple Helix",
        "hypothesis": "—",
    },
    {
        "name": "Diversidade setorial",
        "category": "Demonstração",
        "description": "Complementaridade alta entre setores diferentes.",
        "goal": (
            "Mostrar que a complementaridade entre setores distintos incentiva "
            "mais parcerias que a de mesmo setor."
        ),
        "steps": (
            "Clique em Rodar até o período 60.",
            "No gráfico População e parcerias, acompanhe as parcerias "
            "formadas (marcadores vermelhos).",
            "Em Calibrar, ajuste 'Complementaridade (mesmo setor)' para 0.8 "
            "e rode de novo com a mesma semente para comparar.",
        ),
        "watch_for": (
            "Mais parcerias se formam entre empresas de setores diferentes; a "
            "força das relações (número sobre a aresta) é maior entre complementares."
        ),
        "params": {
            "cross_sector_complementarity": 0.8,
            "same_sector_complementarity": 0.5,
            "n_startups": 14,
        },
        "phenomenon": "Variedade relacionada e complementaridade setorial",
        "reference": "Jacobs (1969); Frenken & Boschma (2007)",
        "hypothesis": "H2",
    },
    {
        "name": "Congestionamento",
        "category": "Demonstração",
        "description": "Muita demanda para pouca infraestrutura.",
        "goal": "Ver o que acontece quando o parque fica cheio demais.",
        "steps": (
            "Clique em Rodar até o período 80.",
            "Observe o indicador Congestionamento passar de 1.",
            "Compare o capital total nos gráficos antes e depois da saturação.",
        ),
        "watch_for": (
            "Custos extras derrubam o capital e reduzem a população; o "
            "congestionamento passa de 1."
        ),
        "params": {"n_startups": 18, "infrastructure_capacity": 8.0},
        "phenomenon": "Retornos crescentes até o limiar de congestionamento",
        "reference": "Arthur (1989, 1996); economia da complexidade (Santa Fe)",
        "hypothesis": "H5",
    },
    {
        "name": "Choque e resiliência",
        "category": "Demonstração",
        "description": "Choque na organização central e recuperação da rede.",
        "goal": (
            "Testar a resiliência da rede: o que acontece após a queda da "
            "organização mais conectada."
        ),
        "steps": (
            "Clique em Rodar até o período 60 e observe a rede antes do choque.",
            "O choque ocorre no período 20 (a empresa mais conectada entra em falha).",
            "Compare as conexões e a população nos períodos seguintes.",
        ),
        "watch_for": (
            "Após o choque, a rede se reconecta aos poucos; novas conexões "
            "aparecem nos períodos seguintes."
        ),
        "params": {
            "shock_period": 20,
            "shock_type": "central_firm",
            "n_anchor_firms": 1,
            "anchor_participation": "active",
            "entry_potential_per_period": 1,
        },
        "phenomenon": "Resiliência da rede após choque",
        "reference": "Holling (1973); Geels (2002)",
        "hypothesis": "H6",
    },
    {
        "name": "Onda de investimento",
        "category": "Demonstração",
        "description": (
            "Investidores ativos e fundo de investimento turbinando aportes."
        ),
        "goal": (
            "Ver uma onda de capital entrar no parque e acelerar o "
            "crescimento das startups."
        ),
        "steps": (
            "Clique em Rodar até o período 60.",
            "No mapa, observe as linhas tracejadas azuis (investimentos) "
            "surgindo entre investidores e startups.",
            "No gráfico População e parcerias, veja o capital e a população "
            "crescerem mais rápido que no cenário padrão.",
        ),
        "watch_for": (
            "Aportes (linhas tracejadas azuis) chegam às startups de maior "
            "qualidade; o capital total cresce em onda."
        ),
        "params": {
            "n_investors": 3,
            "investment_probability": 0.25,
            "policy__investment_fund": 100.0,
            "n_startups": 12,
        },
        "phenomenon": "Onda de investimento em nova tecnologia (surto de capital)",
        "reference": (
            "Perez (2002), Technological Revolutions; Bresnahan & Trajtenberg (1995)"
        ),
        "hypothesis": "—",
    },
    {
        "name": "Missão e política",
        "category": "Demonstração",
        "description": (
            "Infraestrutura compartilhada e matchmaking como política de missão."
        ),
        "goal": (
            "Mostrar que investir em infraestrutura de conexão gera mais "
            "parcerias que um subsídio direto à entrada."
        ),
        "steps": (
            "Clique em Rodar até o período 60.",
            "Observe o indicador Congestionamento ficar baixo "
            "(infraestrutura compartilhada) e as parcerias crescerem "
            "(matchmaking).",
            "Para comparar, troque os parâmetros por 'Subsídio à entrada' "
            "= 0.5 em Calibrar e rode de novo com a mesma semente.",
        ),
        "watch_for": (
            "O congestionamento fica abaixo de 1 por mais tempo e as parcerias "
            "se formam mais cedo que com subsídio à entrada."
        ),
        "params": {
            "policy__shared_infrastructure": 0.5,
            "policy__matchmaking": 0.5,
            "n_startups": 12,
        },
        "phenomenon": (
            "Política de missão: infraestrutura de conexão vs. subsídio à entrada"
        ),
        "reference": "Mazzucato (2013), O Estado Empreendedor",
        "hypothesis": "H4",
    },
    {
        "name": "Dados reais",
        "category": "Demonstração",
        "description": "Atributos de fontes públicas e conexões empíricas.",
        "goal": (
            "Mostrar a camada de dados reais: atributos heterogêneos e regras "
            "de conexão empíricas."
        ),
        "steps": (
            "Clique em Rodar até o período 60.",
            "Na lista Inspecionar, veja escolaridade, idade e salário "
            "dos trabalhadores.",
            "Clique em uma âncora e compare o capital com as demais.",
        ),
        "watch_for": (
            "Trabalhadores e âncoras com atributos variados; investimentos vão "
            "para as startups de maior qualidade."
        ),
        "params": {
            "empirical_init": "aggregates",
            "n_anchor_firms": 2,
            "anchor_participation": "active",
            "connection_profile": "empirical",
            "n_universities": 1,
            "n_investors": 2,
            "n_workers": 8,
        },
        "phenomenon": "Ecossistema empreendedor com atributos empíricos",
        "reference": "Isenberg (2011); Cohen & Levinthal (1990)",
        "hypothesis": "—",
    },
)


@dataclass(frozen=True)
class ParameterSpec:
    """A single calibration control for the workbench."""

    name: str
    label: str
    group: str
    kind: str
    default: Any
    description: str = ""
    simple: bool = False
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    choices: tuple[str, ...] | None = None


def _group_for(name: str) -> str:
    if name == "seed" or name.startswith("n_"):
        return "Population"
    if name.startswith("entry_"):
        return "Entry"
    if name.startswith("partnership_") or name == "productive_tie_strength_threshold":
        return "Partnerships"
    if (
        name in {"rnd_share", "market_access_gain"}
        or name.startswith("knowledge_")
        or name == "innovation_event_threshold"
    ):
        return "Knowledge"
    if name.startswith(("revenue_", "labor_", "hiring_", "investment_", "investor_")):
        return "Finance"
    if name.startswith("congestion_"):
        return "Congestion"
    if (
        name.startswith("shock_")
        or name.startswith("acquisition_")
        or name.startswith("voluntary_")
        or name.startswith("migration_")
    ):
        return "Exits & Shocks"
    if name.startswith(("anchor_", "reputation_")):
        return "Anchors & Reputation"
    if name in {
        "empirical_init",
        "microdata_path",
        "sector_profiles",
        "connection_profile",
        "university_participation",
    }:
        return "Empirical"
    if name.startswith("policy__"):
        return "Policy"
    return "Environment"


def _spec_for(name: str, default: Any) -> ParameterSpec:
    group = _group_for(name)
    label = _LABELS.get(name, name.removeprefix("policy__").replace("_", " "))
    description = _DESCRIPTIONS.get(name, "")
    simple = name in _SIMPLE_FIELDS
    common: dict[str, Any] = {
        "name": name,
        "label": label,
        "group": group,
        "description": description,
        "simple": simple,
        "default": default,
    }
    if name == "seed":
        return ParameterSpec(
            **common, kind="seed", minimum=0, maximum=1_000_000, step=1
        )
    if name == "sectors":
        return ParameterSpec(**common, kind="sectors")
    if name == "microdata_path":
        return ParameterSpec(**common, kind="text")
    if name == "shock_period":
        return ParameterSpec(
            **common, kind="optional_int", minimum=1, maximum=10_000, step=1
        )
    if name == "shock_type":
        return ParameterSpec(**common, kind="optional_choice", choices=SHOCK_TYPES)
    if name in CHOICE_FIELDS:
        return ParameterSpec(**common, kind="choice", choices=CHOICE_FIELDS[name])
    if name in _FLOAT_OVERRIDES:
        minimum, maximum, step = _FLOAT_OVERRIDES[name]
        return ParameterSpec(
            **common,
            kind="float",
            minimum=minimum,
            maximum=maximum,
            step=step,
        )
    if isinstance(default, bool):
        return ParameterSpec(**common, kind="bool")
    if isinstance(default, int):
        return ParameterSpec(**common, kind="int", minimum=0, maximum=100, step=1)
    if name in _PROBABILITY_FIELDS:
        return ParameterSpec(
            **common, kind="probability", minimum=0.0, maximum=1.0, step=0.01
        )
    maximum = max(10.0 * float(default), 10.0)
    step = 0.1 if float(default) >= 10.0 else 0.01
    return ParameterSpec(
        **common, kind="float", minimum=0.0, maximum=maximum, step=step
    )


def parameter_specs() -> list[ParameterSpec]:
    """Return workbench controls covering every configuration field."""
    config = ModelConfig()
    specs: list[ParameterSpec] = []
    for field in fields(ModelConfig):
        if field.name == "policy":
            continue
        specs.append(_spec_for(field.name, getattr(config, field.name)))
    for field in fields(Policy):
        specs.append(
            _spec_for(f"policy__{field.name}", getattr(config.policy, field.name))
        )
    order = {group: index for index, group in enumerate(GROUP_ORDER)}
    return sorted(specs, key=lambda spec: order[spec.group])


def _whole_number(name: str, raw: Any) -> int:
    value = float(raw)
    if not value.is_integer():
        raise ValueError(f"{name} must be a whole number")
    return int(value)


def _coerce(name: str, raw: Any) -> Any:
    if name == "sectors":
        if isinstance(raw, str):
            parts = tuple(part.strip() for part in raw.split(",") if part.strip())
            if not parts:
                raise ValueError("sectors must contain at least one name")
            return parts
        if isinstance(raw, (list, tuple)):
            parts = tuple(str(part) for part in raw if str(part).strip())
            if not parts:
                raise ValueError("sectors must contain at least one name")
            return parts
        raise ValueError("sectors must be a string or a list")
    if name == "seed":
        if raw in (None, ""):
            return None
        return _whole_number(name, raw)
    if name == "shock_period":
        if raw in (None, "", 0, "0"):
            return None
        return _whole_number(name, raw)
    if name == "shock_type":
        if raw in (None, "", "none"):
            return None
        if raw not in SHOCK_TYPES:
            raise ValueError(f"shock_type must be one of {SHOCK_TYPES}")
        return str(raw)
    if name == "microdata_path":
        return str(raw)
    if name in CHOICE_FIELDS:
        if raw not in CHOICE_FIELDS[name]:
            raise ValueError(f"{name} must be one of {CHOICE_FIELDS[name]}")
        return str(raw)
    default = getattr(ModelConfig(), name)
    if isinstance(default, bool):
        return bool(raw)
    if isinstance(default, int):
        return _whole_number(name, raw)
    return float(raw)


def config_from_params(params: Mapping[str, Any]) -> ModelConfig:
    """Build a ModelConfig from dashboard parameters.

    Plain fields and flattened ``policy__`` fields are accepted; unknown keys
    are rejected instead of being silently ignored.
    """
    overrides: dict[str, Any] = {}
    policy_overrides: dict[str, Any] = {}
    config_fields = {field.name for field in fields(ModelConfig)}
    policy_fields = {field.name for field in fields(Policy)}
    for key, raw in params.items():
        if key.startswith("policy__"):
            field_name = key.removeprefix("policy__")
            if field_name not in policy_fields:
                raise ValueError(f"unknown policy parameter: {field_name}")
            policy_overrides[field_name] = float(raw)
        else:
            if key not in config_fields or key == "policy":
                raise ValueError(f"unknown parameter: {key}")
            overrides[key] = _coerce(key, raw)
    if policy_overrides:
        overrides["policy"] = replace(Policy(), **policy_overrides)
    return replace(ModelConfig(), **overrides)


def effective_params(config: ModelConfig) -> dict[str, Any]:
    """Flatten a configuration into workbench parameter values."""
    payload: dict[str, Any] = {}
    for field in fields(ModelConfig):
        if field.name == "policy":
            for policy_field in fields(Policy):
                payload[f"policy__{policy_field.name}"] = getattr(
                    config.policy, policy_field.name
                )
        else:
            value = getattr(config, field.name)
            payload[field.name] = list(value) if isinstance(value, tuple) else value
    return payload


SERIES_LABELS: dict[str, str] = {
    "active_startup_count": "startups ativas",
    "productive_tie_count": "parcerias produtivas",
    "knowledge_mean": "conhecimento médio",
    "innovation_cumulative": "inovações acumuladas",
    "capital_total": "capital total",
    "congestion": "congestionamento",
}

VERDICT_MIN_POINTS = 6


def series_trend(
    history: Sequence[Mapping[str, Any]],
    key: str,
    minimum: int = VERDICT_MIN_POINTS,
) -> dict[str, Any]:
    """Trend of a history series (Mann-Kendall + relative change).

    Pure and deterministic: only looks at the history received. A short
    series yields no verdict — absence of evidence is declared, not filled.
    """
    from .metrics import mann_kendall_trend

    values = [float(record.get(key) or 0.0) for record in history]
    points = len(values)
    if points < minimum:
        return {
            "key": key,
            "points": points,
            "trend": "none",
            "significant": False,
            "change_pct": None,
            "p_value": None,
            "slope": 0.0,
        }
    result = mann_kendall_trend(values)
    first, last = values[0], values[-1]
    change = None if first == 0 else round(100.0 * (last - first) / abs(first), 1)
    return {
        "key": key,
        "points": points,
        "trend": result.trend,
        "significant": result.p_value < 0.05 and result.trend != "none",
        "change_pct": change,
        "p_value": round(result.p_value, 4),
        "slope": result.slope,
    }


def _p(trend: Mapping[str, Any]) -> str:
    value = trend.get("p_value")
    if not isinstance(value, (int, float)):
        return "n/d"
    if 0 <= value < 0.0005:
        return "<0,001"
    return f"{value:.3f}".replace(".", ",")


def _verdict_text(trend: Mapping[str, Any], label: str) -> str:
    points = int(trend.get("points") or 0)
    if trend.get("p_value") is None:
        return f"{label}: série curta ({points} períodos) — sem veredito"
    change = trend.get("change_pct")
    mudanca = (
        f"{abs(change):.1f}%".replace(".", ",")
        if isinstance(change, (int, float))
        else "—"
    )
    if not trend.get("significant"):
        return f"sem tendência detectável em {points} períodos"
    if trend.get("trend") == "increasing":
        return (
            f"subiu {mudanca} em {points} períodos (tendência crescente, p={_p(trend)})"
        )
    if trend.get("trend") == "decreasing":
        return (
            f"caiu {mudanca} em {points} períodos (tendência de queda, p={_p(trend)})"
        )
    return f"sem tendência detectável em {points} períodos"


def series_verdicts(history: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """One verdict line per workbench metric (Mann-Kendall + window + p)."""
    verdicts: dict[str, str] = {}
    for key in (
        "active_startup_count",
        "productive_tie_count",
        "knowledge_mean",
        "innovation_cumulative",
        "capital_total",
    ):
        verdicts[key] = _verdict_text(series_trend(history, key), SERIES_LABELS[key])
    if history and float(history[-1].get("congestion") or 0.0) > 1.0:
        verdicts["congestion"] = (
            "acima do limiar de saturação (1,0) — custo extra por organização"
        )
    else:
        verdicts["congestion"] = _verdict_text(
            series_trend(history, "congestion"), SERIES_LABELS["congestion"]
        )
    return verdicts


def synthesis_block(
    history: Sequence[Mapping[str, Any]],
    config: ModelConfig,
) -> dict[str, Any]:
    """Synthesis block for the Concluir step: verdict + three trends + alert.

    Same shape as the dashboard block it descends from (verdict, trends,
    alert, severity). The three trends are population, knowledge mean, and
    productive ties — the workbench's own metrics, not the dashboard's
    ``knowledge_total``/``reputation``. The verdict scopes to "População"
    only (C4).
    """
    if not history:
        return {
            "verdict": "Sem leitura ainda: execute a investigação para ver o parque.",
            "trends": [],
            "alert": None,
            "severity": "info",
        }
    latest = history[-1]
    period = int(latest.get("period") or 0)
    pop = series_trend(history, "active_startup_count")
    know = series_trend(history, "knowledge_mean")
    ties = series_trend(history, "productive_tie_count")
    congestion = float(latest.get("congestion") or 0.0)

    if pop.get("significant") and pop.get("trend") == "increasing":
        estado = "População em expansão"
    elif pop.get("significant") and pop.get("trend") == "decreasing":
        estado = "População em retração"
    else:
        estado = "População estável"
    verdict = (
        f"{estado}: {int(latest.get('active_startup_count') or 0)} startups ativas, "
        f"conhecimento médio "
        f"{f'{float(latest.get("knowledge_mean") or 0.0):.2f}'.replace('.', ',')} "
        f"e {int(latest.get('productive_tie_count') or 0)} parcerias produtivas "
        f"no período {period}."
    )

    alert = None
    severity = "info"
    if congestion > 1.0:
        alert = (
            "Congestionamento acima de 1: a infraestrutura está saturada e cada "
            "organização paga custo extra."
        )
        severity = "warn"
    elif pop.get("significant") and pop.get("trend") == "decreasing":
        alert = (
            "População caindo de forma consistente: compare as saídas entre períodos."
        )
        severity = "warn"
    elif config.shock_period is not None and period == int(config.shock_period):
        alert = "O choque programado caiu neste período: compare a rede antes e depois."
        severity = "warn"

    return {
        "verdict": verdict,
        "trends": [
            {
                "label": SERIES_LABELS[key],
                "text": _verdict_text(trend, SERIES_LABELS[key]),
                "significant": bool(trend.get("significant")),
            }
            for key, trend in (
                ("active_startup_count", pop),
                ("knowledge_mean", know),
                ("productive_tie_count", ties),
            )
        ],
        "alert": alert,
        "severity": severity,
    }


def _grid_positions(
    ids: Sequence[int],
    region: Mapping[str, Any],
) -> dict[int, tuple[float, float]]:
    """Place nodes of one type on a deterministic grid inside a region."""
    if not ids:
        return {}
    x0, x1 = float(region["x0"]), float(region["x1"])
    y0, y1 = float(region["y0"]), float(region["y1"])
    columns = math.ceil(math.sqrt(len(ids)))
    rows = math.ceil(len(ids) / columns)
    positions: dict[int, tuple[float, float]] = {}
    for index, node_id in enumerate(ids):
        column = index % columns
        row = index // columns
        fraction_x = 0.5 if columns == 1 else column / (columns - 1)
        fraction_y = 0.5 if rows == 1 else row / (rows - 1)
        positions[node_id] = (
            x0 + (x1 - x0) * fraction_x,
            y1 - (y1 - y0) * fraction_y,
        )
    return positions


def nodes_of(model: TechnologyParkModel) -> list[dict[str, Any]]:
    """Map nodes for a model instance (type/attributes only, no layout)."""
    nodes: list[dict[str, Any]] = []
    for startup in model.startups:
        if not startup.alive:
            continue
        nodes.append(
            {
                "id": startup.startup_id,
                "type": "startup",
                "sector": startup.sector,
                "capital": startup.capital,
                "knowledge": startup.knowledge,
                "reputation": startup.reputation,
                "team_size": startup.team_size,
                "age": startup.age,
            }
        )
    for anchor in model.anchor_firms:
        nodes.append(
            {
                "id": anchor.firm_id,
                "type": "anchor",
                "sector": anchor.sector,
                "capital": anchor.capital,
                "knowledge": anchor.knowledge,
                "reputation": anchor.reputation,
                "participation": anchor.participation,
            }
        )
    for investor in model.investors:
        nodes.append(
            {
                "id": investor.investor_id,
                "type": "investor",
                "capital": investor.capital_available,
                "active": investor.active,
            }
        )
    for worker in model.workers:
        nodes.append(
            {
                "id": worker.worker_id,
                "type": "worker",
                "sector": worker.sector,
                "skill": worker.skill,
                "education": worker.education,
                "age": worker.age,
                "wage": worker.wage,
                "employed_by": worker.employed_by,
            }
        )
    for university in model.universities:
        nodes.append(
            {
                "id": int(university.unique_id or 0),
                "type": "university",
                "knowledge_stock": university.knowledge_stock,
            }
        )
    return nodes


def layout_of(
    nodes: Sequence[Mapping[str, Any]],
) -> dict[int, tuple[float, float]]:
    """Deterministic ecosystem map: each agent type gets its own region.

    Positions depend only on node ids and types, so the picture is stable
    across periods and reproducible.
    """
    by_type: dict[str, list[int]] = {str(region["key"]): [] for region in REGIONS}
    for node in nodes:
        by_type.setdefault(str(node["type"]), []).append(int(node["id"]))
    positions: dict[int, tuple[float, float]] = {}
    for region in REGIONS:
        ids = sorted(by_type.get(str(region["key"]), []))
        positions.update(_grid_positions(ids, region))
    return positions


class MapSession:
    """Minimal deterministic session backing workbench map frames.

    Holds one TechnologyParkModel; ``step`` advances it and ``state``
    exposes the same period/nodes/edges/positions/regions shapes the
    former dashboard session provided. No history, sweeps, references,
    or replays — the workbench records its own trajectories.
    """

    def __init__(self, params: Mapping[str, Any] | None = None) -> None:
        self._config = config_from_params(dict(params or {}))
        self._model = TechnologyParkModel(config=self._config)

    def step(self, count: int = 1) -> None:
        """Advance the model ``count`` periods."""
        if count < 1:
            raise ValueError("step count must be at least 1")
        for _ in range(count):
            self._model.advance()

    def state(self) -> dict[str, Any]:
        """Return the visualizable map state (network + layout)."""
        nodes = nodes_of(self._model)
        edges = [
            {
                "source": first,
                "target": second,
                "type": tie_type,
                "strength": strength,
            }
            for first, second, tie_type, strength in self._model.network.entries()
        ]
        layout = layout_of(nodes)
        return {
            "period": self._model.period,
            "nodes": nodes,
            "edges": edges,
            "positions": {
                str(agent_id): [position[0], position[1]]
                for agent_id, position in layout.items()
            },
            "regions": [dict(region) for region in REGIONS],
        }

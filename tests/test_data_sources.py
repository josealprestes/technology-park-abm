"""Real-data ingestion helpers: CNPJ sample summaries and catalog validation."""

from __future__ import annotations

from pathlib import Path

from technology_park_abm.data_pipeline import summarize_company_sample


def test_summarize_company_sample_computes_aggregates() -> None:
    rows = [
        {
            "porte": "DEMAIS",
            "capital_social": 10.0,
            "data_inicio_atividade": "2000-01-01",
        },
        {
            "porte": "DEMAIS",
            "capital_social": 30.0,
            "data_inicio_atividade": "1990-01-01",
        },
        {
            "porte": "ME",
            "capital_social": 20.0,
            "data_inicio_atividade": "2016-01-01",
        },
    ]
    summary = summarize_company_sample(rows)
    assert summary["count"] == 3
    assert summary["porte_shares"]["DEMAIS"] == 2 / 3
    assert summary["capital_median"] == 20.0
    assert summary["capital_min"] == 10.0
    assert summary["capital_max"] == 30.0
    assert summary["age_median"] == 26.0


def test_summarize_company_sample_rejects_empty() -> None:
    try:
        summarize_company_sample([])
    except ValueError:
        pass
    else:
        raise AssertionError("empty sample should fail")


def test_catalog_contains_real_sources() -> None:
    import json

    from technology_park_abm.data_pipeline import load_catalog

    sources = load_catalog(Path("data") / "manifest.json")
    names = {entry["name"] for entry in sources}
    assert "worldbank_tech_exports_brazil" in names
    assert "worldbank_patents_brazil" in names
    assert "brasilapi_cnpj_sample" in names
    assert "worldbank_rnd_brazil" not in names
    exports = next(
        entry for entry in sources if entry["name"] == "worldbank_tech_exports_brazil"
    )
    assert exports["status"] == "downloaded"
    assert exports["sha256"]
    assert json.dumps(exports)


def test_catalog_carries_sidra_aggregates_and_legal_fields() -> None:
    from technology_park_abm.data_pipeline import load_catalog

    sources = load_catalog(Path("data") / "manifest.json")
    by_name = {entry["name"]: entry for entry in sources}
    sidra_sources = [
        "ibge_pnadc_educacao_ocupados",
        "ibge_pnadc_rendimento_instrucao",
        "ibge_pnadc_ocupados_idade",
        "ibge_cempre_pessoal_secao_cnae",
        "ibge_demografia_nascimentos_sobrevivencia",
    ]
    for name in sidra_sources:
        entry = by_name[name]
        assert entry["status"] == "downloaded"
        assert entry["sha256"]
        assert entry["personal_data"] == "aggregated"
        assert "apisidra.ibge.gov.br" in entry["url"]
    for name in (
        "mte_rais_microdata",
        "mte_novo_caged_microdata",
        "mte_caged_estatistico",
    ):
        entry = by_name[name]
        assert entry["status"] == "catalog-only"
        assert entry["personal_data"] == "personal"
        assert entry["sha256"] is None
    for entry in sources:
        assert entry["legal_basis"]
        assert entry["personal_data"] in {"none", "aggregated", "personal"}

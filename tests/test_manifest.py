import json

from technology_park_abm import (
    METRIC_SCHEMA_VERSION,
    ModelConfig,
    build_manifest,
    git_commit,
    git_dirty,
)


def test_manifest_captures_configuration_and_versions() -> None:
    config = ModelConfig(n_startups=3, seed=5)
    manifest = build_manifest(config)
    assert manifest["schema_version"] == "1.0"
    assert manifest["experiment"]["parameters"]["seed"] == 5
    assert manifest["experiment"]["parameters"]["n_startups"] == 3
    assert manifest["experiment"]["seeds"] == [5]
    assert manifest["model"]["metric_schema_version"] == METRIC_SCHEMA_VERSION
    assert isinstance(manifest["model"]["package_version"], str)
    assert isinstance(manifest["model"]["git_commit"], str | None)
    assert isinstance(manifest["model"]["git_dirty"], bool | None)
    assert isinstance(manifest["environment"]["python"], str)
    assert isinstance(manifest["environment"]["mesa"], str)
    assert isinstance(manifest["environment"]["platform"], str)
    assert isinstance(manifest["created_utc"], str)


def test_manifest_embeds_the_full_configuration() -> None:
    config = ModelConfig()
    parameters = build_manifest(config)["experiment"]["parameters"]
    assert parameters["entry_potential_per_period"] == (
        config.entry_potential_per_period
    )
    assert parameters["sectors"] == config.sectors
    assert parameters["policy"]["matchmaking"] == 0.0


def test_manifest_is_json_serializable() -> None:
    manifest = build_manifest(ModelConfig())
    json.dumps(manifest)
    assert "not empirical" in manifest["notice"].lower()


def test_git_helpers_return_expected_types() -> None:
    commit = git_commit()
    assert commit is None or isinstance(commit, str)
    dirty = git_dirty()
    assert dirty is None or isinstance(dirty, bool)

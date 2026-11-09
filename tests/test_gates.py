"""Deterministic skill gates: static scans, docs-sync, and manifest fields.

Each test maps a skill rule to an automated check (see the gate table in
``AGENTS.md``): no unseeded randomness or wall-clock time in ``src``
(adversarial review, Phase 2), no network access outside the data pipeline
and the loopback workbench (ADR 0004), ODD/TRACE documentation completeness
(adversarial review, Phase 5), test-plan traceability in sync with test files
(testing skill), STRESS-style manifest fields (adversarial review, Phase 5),
and the gate runner exposing the documented gates in order (workflow skill).
G13 pins the workbench as one self-contained surface (no external requests,
embedded fonts, no chart libraries). G16 checks that the research-software
metadata (`CITATION.cff`, `codemeta.json`, `.zenodo.json`, `SECURITY.md`,
`CHANGELOG.md`) exists and stays in sync with `pyproject.toml`
(rse-reproducibility skill).

Retired with the dashboard (v2.15.0): the single-file dashboard contract,
UX interaction/dataviz contracts (G14/G15), the journey/suite contracts
(G10/G11), and the mobile shell (G17). The workbench owns its contracts in
`tests/test_investigation_prototype.py`.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import tomllib
from pathlib import Path

import pytest

from technology_park_abm.config import ModelConfig
from technology_park_abm.manifest import MANIFEST_SCHEMA_VERSION, build_manifest
from technology_park_abm.metrics import METRIC_SCHEMA_VERSION

pytestmark = [pytest.mark.unit, pytest.mark.gate]

SRC = Path("src/technology_park_abm")
PROTOTYPES = Path("docs/prototypes")
FONTS = PROTOTYPES / "fonts/geist-embedded.css"

_TIME_ATTRS = {"time", "monotonic", "perf_counter", "process_time"}
_OS_ATTRS = {"urandom", "getpid"}

_NETWORK_ROOTS = {"requests", "urllib", "http", "socket", "ssl", "websocket"}
_NETWORK_ALLOW: dict[str, set[str]] = {
    "data_pipeline.py": {"urllib.request", "urllib.error", "urllib.parse"},
}

_WALLCLOCK_FILES = {
    "manifest.py",
    "experiments.py",
    "sensitivity.py",
    "data_pipeline.py",
}


def _trees() -> dict[str, ast.Module]:
    trees: dict[str, ast.Module] = {}
    for path in sorted(SRC.glob("*.py")):
        trees[path.name] = ast.parse(path.read_text(encoding="utf-8"))
    return trees


def test_no_unseeded_randomness_or_wallclock() -> None:
    offenders: list[str] = []
    for name, tree in _trees().items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name):
                if func.id == "hash":
                    offenders.append(f"{name}: bare hash() is not stable")
                continue
            if not isinstance(func, ast.Attribute):
                continue
            if not isinstance(func.value, ast.Name):
                continue
            module, attr = func.value.id, func.attr
            if module == "random" and attr != "Random":
                offenders.append(f"{name}: unseeded random.{attr}() call")
            elif module == "time" and attr in _TIME_ATTRS:
                offenders.append(f"{name}: wall-clock time.{attr}() call")
            elif module == "os" and attr in _OS_ATTRS:
                offenders.append(f"{name}: os.{attr}() call")
            elif module == "secrets":
                offenders.append(f"{name}: secrets.{attr}() call")
    assert offenders == []


def test_no_network_outside_allowlist() -> None:
    offenders: list[str] = []
    for name, tree in _trees().items():
        allowed = _NETWORK_ALLOW.get(name, set())
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules = [node.module]
            for module in modules:
                root = module.split(".")[0]
                if root in _NETWORK_ROOTS | {"webbrowser"} and module not in allowed:
                    offenders.append(f"{name}: network import {module}")
    assert offenders == []


def test_wallclock_only_in_manifest_layer() -> None:
    offenders: list[str] = []
    for name, tree in _trees().items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "now"
                and isinstance(func.value, ast.Name)
                and func.value.id == "datetime"
                and name not in _WALLCLOCK_FILES
            ):
                offenders.append(name)
    assert offenders == []


def test_docs_spec_has_odd_and_trace() -> None:
    text = Path("docs/model-specification.md").read_text(encoding="utf-8")
    assert "## ODD-aligned model description" in text
    for section in (
        "### 1. Purpose and patterns",
        "### 2. Entities, state variables, and scales",
        "### 3. Process overview and scheduling",
        "### 4. Design concepts",
        "### 5. Initialization",
        "### 6. Input data",
        "### 7. Submodels",
    ):
        assert section in text
    assert "## TRACE traceability" in text
    assert "| TRACE element | Artifact |" in text


def test_testplan_traceability_files_exist() -> None:
    text = Path("docs/test-plan.md").read_text(encoding="utf-8")
    section = text.split("## 10. Traceability", 1)[1].split("## References", 1)[0]
    names = sorted(set(re.findall(r"`(test_[a-z0-9_]+)`", section)))
    assert names
    missing = [name for name in names if not Path(f"tests/{name}.py").exists()]
    assert missing == []


def test_manifest_carries_stress_fields() -> None:
    manifest = build_manifest(ModelConfig(seed=7))
    assert manifest["schema_version"] == MANIFEST_SCHEMA_VERSION
    assert manifest["schema_version"] == "1.0"
    assert "not empirical" in manifest["notice"].lower()
    experiment = manifest["experiment"]
    assert experiment["seeds"] == [7]
    assert experiment["parameters"]["seed"] == 7
    model = manifest["model"]
    assert model["metric_schema_version"] == METRIC_SCHEMA_VERSION
    assert model["package_version"]
    assert "git_commit" in model and "git_dirty" in model
    environment = manifest["environment"]
    assert environment["python"] and environment["mesa"] and environment["platform"]


def test_research_software_metadata_in_sync() -> None:
    """G16: research-software metadata exists and matches pyproject.toml."""
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    version = pyproject["project"]["version"]

    for name in (
        "CITATION.cff",
        "codemeta.json",
        ".zenodo.json",
        "SECURITY.md",
        "CHANGELOG.md",
    ):
        assert Path(name).is_file(), f"missing research-software metadata: {name}"

    # The workbench provenance reads `package_version()` (installed metadata),
    # not pyproject. With a stale editable install the health endpoint would
    # advertise the old version. This gate closes the hole.
    from technology_park_abm.manifest import package_version

    assert package_version() == version, (
        f"metadados instalados ({package_version()}) divergem de pyproject.toml "
        f"({version}) — rode `pip install -e .` no venv"
    )

    cff = Path("CITATION.cff").read_text(encoding="utf-8")
    cff_version = re.search(r"^version:\s*(\S+)", cff, flags=re.M)
    cff_date = re.search(r"^date-released:\s*(\S+)", cff, flags=re.M)
    assert cff_version is not None, "CITATION.cff has no top-level version"
    assert cff_version.group(1) == version
    assert cff_date is not None, "CITATION.cff has no top-level date-released"

    codemeta = json.loads(Path("codemeta.json").read_text(encoding="utf-8"))
    assert codemeta["version"] == version
    assert codemeta["datePublished"] == cff_date.group(1)

    zenodo = json.loads(Path(".zenodo.json").read_text(encoding="utf-8"))
    assert zenodo["version"] == version

    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    first_release = re.search(r"^## \[(\d+\.\d+\.\d+)\]", changelog, flags=re.M)
    assert first_release is not None, "CHANGELOG.md has no release section"
    assert first_release.group(1) == version


def test_gate_runner_lists_documented_gates() -> None:
    spec = importlib.util.spec_from_file_location(
        "check_gates", Path("scripts/check_gates.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    gates = module.GATES
    assert [name for name, _ in gates] == ["lint", "format", "types", "tests"]
    tests_argv = dict(gates)["tests"]
    assert "--cov" in tests_argv
    assert "error::DeprecationWarning" in tests_argv
    assert "error::FutureWarning" in tests_argv


def test_workbench_is_selfcontained_loopback_only() -> None:
    """G13 (workbench): sources make no external requests and pull no libs.

    The built page inlines data, code, and fonts; the only fetch targets are
    same-origin loopback ``/api/investigation/`` calls.
    """
    sources = "".join(
        (PROTOTYPES / name).read_text(encoding="utf-8")
        for name in (
            "investigation.html",
            "investigation-prepare.html",
            "investigation.js",
            "investigation-setup.js",
            "investigation-view.js",
        )
    )
    assert "<script src" not in sources
    assert '<link rel="stylesheet" href="http' not in sources
    assert "@import url(http" not in sources
    for match in re.finditer(r"https?://[^\s\"'<>]+", sources):
        url = match.group(0)
        assert "doi.org" in url or "nber.org" in url or "w3.org" in url, url
    assert "fetch(path" in sources, "expected loopback API calls in the sources"
    for target in re.findall(r"['\"](/api/[^'\"]*)['\"]", sources):
        assert target.startswith("/api/investigation/"), target
    assert "XMLHttpRequest" not in sources
    assert "WebSocket(" not in sources


def test_workbench_fonts_are_embedded_and_licensed() -> None:
    """G13: typography travels with the workbench — 4 Geist @font-face.

    The licensed base64 WOFF2 lives in the committed
    ``docs/prototypes/fonts/geist-embedded.css`` (the builder inlines it);
    the dashboard file it was extracted from is retired.
    """
    assert not (SRC / "static" / "dashboard.html").exists()
    assert FONTS.is_file()
    css = FONTS.read_text(encoding="utf-8")
    assert css.count("@font-face") == 4
    sources = re.findall(r"src:\s*url\(([^)]+)\)", css)
    assert len(sources) == 4
    for source in sources:
        assert source.startswith("data:font/woff2;base64,"), source[:40]
    assert (Path("licenses") / "OFL-Geist.txt").exists()


def test_workbench_has_no_chart_libraries() -> None:
    """G13: the workbench draws its own canvas — no chart/viz libraries."""
    sources = "".join(
        (PROTOTYPES / name).read_text(encoding="utf-8").lower()
        for name in ("investigation.html", "investigation.js", "investigation-view.js")
    )
    for token in (
        "chart.js",
        "chartjs",
        "plotly",
        "highcharts",
        "echarts",
        "three.js",
        "donut",
        "gauge",
    ):
        assert token not in sources, token
    assert "d3.select" not in sources


def test_no_dashboard_remnants() -> None:
    """The dashboard shell is retired: no module, asset, test, or script."""
    assert not (SRC / "dashboard.py").exists()
    assert not (SRC / "static").exists()
    for name in (
        "test_dashboard.py",
        "test_ui_contracts.py",
        "test_journey_gates.py",
        "test_map_visualization.py",
        "test_mobile_contracts.py",
        "test_uj_contracts.py",
        "test_a11y_browser.py",
    ):
        assert not (Path("tests") / name).exists(), name
    for name in ("screenshots.py", "uj_metrics.py", "verificar_arestas.py"):
        assert not (Path("scripts") / name).exists(), name
    tree = ast.parse((SRC / "workbench_core.py").read_text(encoding="utf-8"))
    top: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            top.add(node.name)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            top.add(node.target.id)
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            top.add(node.targets[0].id)
    for legacy in (
        "DashboardSession",
        "SweepRunner",
        "dashboard_html",
        "create_server",
        "serve",
    ):
        assert legacy not in top, legacy


def test_workbench_server_refuses_stale_page_and_reports_identity() -> None:
    """G13: the server pins the served page (sha + build stamp + boot time).

    A page older than any prototype source means the deploy skipped the
    mandatory rebuild — the constructor raises instead of serving it.
    The health payload carries the identity so the deploy proof binds the
    page to the commit, not just the installed package.
    """
    import hashlib
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "workbench_server", Path("scripts/serve_investigation_prototype.py")
    )
    assert spec is not None and spec.loader is not None
    server_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server_module)

    info = server_module._page_info(Path("outputs/investigation"))
    assert info["page_sha256"]
    stamp = info["page_stamp"]
    assert stamp["version"]
    assert stamp["git_commit"]
    page_text = Path("outputs/investigation/index.html").read_text(encoding="utf-8")
    assert stamp["page_sha256"] == hashlib.sha256(page_text.encode("utf-8")).hexdigest()
    src = Path("scripts/serve_investigation_prototype.py").read_text(encoding="utf-8")
    assert '"workbench_schema": 4' in src
    assert '"started_utc"' in src and '"page"' in src

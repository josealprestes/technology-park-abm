"""Build a self-contained journey prototype from actual, paired model runs.

Builds cached examples for the optional local workbench, not a replacement
dashboard or a new scientific experiment. No simulation output is committed:
  .venv/Scripts/python.exe scripts/build_investigation_prototype.py
  .venv/Scripts/python.exe scripts/serve_investigation_prototype.py --port 8777
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import platform
import re
from collections.abc import Sequence
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import Any

from technology_park_abm.investigation import METRICS, run_scenario
from technology_park_abm.manifest import (
    git_commit,
    git_dirty,
    mesa_version,
    package_version,
)
from technology_park_abm.metrics import METRIC_SCHEMA_VERSION
from technology_park_abm.workbench_core import (
    DEMO_PLAYBOOKS,
    parameter_specs,
)

ROOT = Path(__file__).resolve().parent.parent
HORIZONS = (20, 40, 60, 80)
SEEDS = tuple(range(1, 9))
CAPACITIES = {"A": 8.0, "B": 24.0}


def build_evidence(seeds: Sequence[int] = SEEDS) -> dict[str, Any]:
    """Return complete configurations, paired trajectories and first-seed maps."""
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("Informe sementes distintas e não vazias.")
    research = json.loads(
        (ROOT / "docs/prototypes/investigation-scenarios.json").read_text(
            encoding="utf-8"
        )
    )
    scenarios = []
    for index, playbook in enumerate(DEMO_PLAYBOOKS):
        scenarios.append(
            {
                "id": f"tour-{index + 1}",
                "name": playbook["name"],
                "description": playbook["description"],
                "phenomenon": playbook["phenomenon"],
                "reference": playbook["reference"],
                "hypothesis": playbook["hypothesis"],
                **run_scenario(dict(playbook["params"]), seeds),
            }
        )
    scenarios.append(
        {
            "id": "capacity-24",
            "name": "Congestionamento · capacidade ampliada",
            "description": "Mesmo roteiro Congestionamento, com capacidade 24.",
            "phenomenon": "Comparação exploratória de capacidade",
            "reference": "Variação do roteiro Congestionamento",
            "hypothesis": "H5 (exploração; não é o experimento E5)",
            **run_scenario({"n_startups": 18, "infrastructure_capacity": 24.0}, seeds),
        }
    )
    for scenario_id, dossier in research["scenarios"].items():
        if "params" in dossier:
            scenarios.append(
                {
                    "id": scenario_id,
                    "name": dossier["name"],
                    **run_scenario(dossier["params"], seeds),
                }
            )
    for item in scenarios:
        dossier = research["scenarios"][item["id"]]
        item["original_name"] = item["name"]
        item["name"] = dossier["name"]
        item["description"] = dossier["watch"]
        item["phenomenon"] = dossier["question"]
        item["hypothesis"] = dossier["hypothesis_id"]
        item["reference"] = "; ".join(
            research["sources"][key]["citation"] for key in dossier["sources"]
        )
        item["research"] = dossier
    conditions = {"A": scenarios[4], "B": scenarios[9]}
    return {
        "schema": "investigation-prototype-2",
        "simulation": True,
        "question": "O que muda quando aumentamos a capacidade do parque?",
        "hypothesis": "H5 (exploração; não é o experimento E5)",
        "changed_parameter": "infrastructure_capacity",
        "seeds": list(seeds),
        "horizons": list(HORIZONS),
        "metrics": list(METRICS),
        "scenarios": scenarios,
        "research": research,
        "parameters": [asdict(spec) for spec in parameter_specs()],
        "parameter_labels": {spec.name: spec.label for spec in parameter_specs()},
        "version": package_version(),
        "runtime": {
            "python": platform.python_version(),
            "mesa": mesa_version(),
            "networkx": version("networkx"),
            "metric_schema": METRIC_SCHEMA_VERSION,
        },
        "git_commit": git_commit(),
        "git_dirty": git_dirty(),
        "source_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(
                [
                    *(ROOT / "src/technology_park_abm").rglob("*.py"),
                    ROOT / "docs/prototypes/fonts/geist-embedded.css",
                    ROOT / "scripts/build_investigation_prototype.py",
                    *(ROOT / "docs/prototypes").glob("investigation*"),
                    ROOT / "scripts/serve_investigation_prototype.py",
                    ROOT / "uv.lock",
                ]
            )
        },
        "conditions": conditions,
    }


def render_prototype(evidence: dict[str, Any]) -> str:
    """Embed data and the licensed Geist fonts; no runtime fetches."""
    template = (ROOT / "docs/prototypes/investigation.html").read_text(encoding="utf-8")
    fonts = (ROOT / "docs/prototypes/fonts/geist-embedded.css").read_text(
        encoding="utf-8"
    )
    script = (ROOT / "docs/prototypes/investigation.js").read_text(encoding="utf-8")
    setup = (ROOT / "docs/prototypes/investigation-setup.js").read_text(
        encoding="utf-8"
    )
    view = (ROOT / "docs/prototypes/investigation-view.js").read_text(encoding="utf-8")
    script = script.replace("/* SETUP_HELPERS */", setup)
    script = script.replace("/* RENDER_FUNCTION */", view)
    script = script.replace("/* NAVIGATION_FUNCTION */", "")
    prepare = (ROOT / "docs/prototypes/investigation-prepare.html").read_text(
        encoding="utf-8"
    )
    template = template.replace("<!-- PREPARE_SCREEN -->", prepare)
    # Conditions alias two scenarios in Python; avoid duplicating their frames.
    compact = {**evidence, "conditions": {"A": "tour-5", "B": "capacity-24"}}
    payload = json.dumps(
        compact, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    )
    # Native browser decompression keeps all network frames portable without
    # transferring megabytes of repeated JSON keys. mtime=0 preserves byte identity.
    packed = base64.b64encode(gzip.compress(payload.encode("utf-8"), mtime=0)).decode(
        "ascii"
    )
    template = re.sub(r"<button\b", "<button disabled", template)
    return (
        template.replace("/* EMBEDDED_FONTS */", fonts)
        .replace("/* EMBEDDED_SCRIPT */", script)
        .replace("__EVIDENCE_JSON__", packed)
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "outputs/investigation/index.html"
    )
    args = parser.parse_args(argv)
    evidence = build_evidence()
    rendered = render_prototype(evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    stamp = {
        "version": evidence["version"],
        "git_commit": evidence["git_commit"],
        "git_dirty": evidence["git_dirty"],
        "page_sha256": digest,
    }
    (args.output.parent / "build.json").write_text(
        json.dumps(stamp, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Protótipo: {args.output}")
    count = len(evidence["scenarios"]) * len(evidence["seeds"])
    print(f"{count} execuções; {len(evidence['scenarios'])} opções; SHA256 {digest}")
    print(
        f"Build: {evidence['version']} @ "
        f"{evidence['git_commit'] or 'sem-commit'}"
        f"{' (árvore com alterações)' if evidence['git_dirty'] else ''} → build.json"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

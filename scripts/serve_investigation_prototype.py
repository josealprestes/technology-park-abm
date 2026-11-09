"""Serve the optional investigation workbench and its real-model jobs locally.

Usage: python scripts/serve_investigation_prototype.py --port 8777
Only loopback is supported. Results stay in memory and are exported by the UI.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import threading
from concurrent.futures import CancelledError
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from pathlib import Path
from typing import Any, cast

from technology_park_abm.investigation import run_scenario, validate_investigation
from technology_park_abm.manifest import (
    git_commit,
    git_dirty,
    mesa_version,
    package_version,
)
from technology_park_abm.metrics import METRIC_SCHEMA_VERSION
from technology_park_abm.workbench_core import (
    _translate_error,
    series_verdicts,
    synthesis_block,
)

ROOT = Path(__file__).resolve().parent.parent

STARTED_UTC = datetime.now(UTC).isoformat()


def _page_info(directory: Path) -> dict[str, Any]:
    """Identity of the served page: hash + build stamp + freshness.

    The page is generated (gitignored); the stamp comes from the sibling
    ``build.json`` the builder writes. A page older than any prototype
    source means the deploy skipped the mandatory rebuild — the server
    refuses to start instead of serving a stale edition.
    """
    page = directory / "index.html"
    stamp_path = directory / "build.json"
    if not page.is_file():
        raise SystemExit(
            f"Página não encontrada em {page}: rode "
            "scripts/build_investigation_prototype.py antes de servir."
        )
    newest_source = max(
        path.stat().st_mtime
        for path in [
            *(ROOT / "src/technology_park_abm").glob("*.py"),
            ROOT / "scripts/build_investigation_prototype.py",
            ROOT / "scripts/serve_investigation_prototype.py",
            *(ROOT / "docs/prototypes").glob("investigation*"),
            ROOT / "docs/prototypes/fonts/geist-embedded.css",
        ]
    )
    if page.stat().st_mtime < newest_source:
        raise SystemExit(
            f"Página desatualizada em {page} (fontes mais novas): rode "
            "scripts/build_investigation_prototype.py antes de servir."
        )
    digest = hashlib.sha256(page.read_bytes()).hexdigest()
    stamp: dict[str, Any] = {}
    if stamp_path.is_file():
        try:
            stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            stamp = {}
    return {"page_sha256": digest, "page_stamp": stamp}


def _flat_config(config: dict[str, Any], seed: int) -> dict[str, Any]:
    """Flatten a run config (nested ``policy``) back into params form."""
    flat = dict(config.get("policy", {}))
    out = {f"policy__{key}": value for key, value in flat.items()}
    out.update({key: value for key, value in config.items() if key != "policy"})
    out["seed"] = seed
    return out


def _verdicts_for(result: dict[str, Any]) -> dict[str, Any]:
    """Synthesis + per-series Mann-Kendall verdicts for a live job result.

    Trends run on the per-period mean across seeds (same aggregation the
    trajectory chart paints); p10-p90 stays the uncertainty display, never
    a confidence interval. The metric definition travels with the verdicts
    so a changed productive-tie threshold cannot silently move the reading.
    """
    from technology_park_abm.investigation import METRICS
    from technology_park_abm.workbench_core import config_from_params

    runs = result.get("runs", [])
    periods = sorted(
        {record["period"] for run in runs for record in run.get("history", [])}
    )
    history: list[dict[str, Any]] = []
    for period in periods:
        entry: dict[str, Any] = {"period": period}
        for key in METRICS:
            values = [
                float(record[key])
                for run in runs
                for record in run.get("history", [])
                if record.get("period") == period and record.get(key) is not None
            ]
            entry[key] = sum(values) / len(values) if values else 0.0
        history.append(entry)
    config = config_from_params(_flat_config(result.get("config", {}), runs[0]["seed"]))
    return {
        "verdicts": series_verdicts(history),
        "synthesis": synthesis_block(history, config),
        "verdict_metric_definition": {
            "metrics": list(METRICS),
            "aggregation": "mean across seeds per period",
            "productive_tie_strength_threshold": result.get("config", {}).get(
                "productive_tie_strength_threshold"
            ),
        },
    }


def provenance() -> dict[str, Any]:
    sources = [
        *(ROOT / "src/technology_park_abm").glob("*.py"),
        ROOT / "scripts/serve_investigation_prototype.py",
        *(ROOT / "docs/prototypes").glob("investigation*"),
        ROOT / "uv.lock",
    ]
    return {
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
            path.relative_to(ROOT).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(sources)
        },
    }


class Jobs:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.metadata = provenance()
        self.items: dict[str, dict[str, Any]] = {}
        self.counter = 0

    def start(self, body: dict[str, Any]) -> str:
        mode = body.get("mode")
        if mode not in ("observe", "compare"):
            raise ValueError("Escolha observar um cenário ou comparar dois.")
        conditions = body.get("conditions")
        keys = ["A"] if mode == "observe" else ["A", "B"]
        if not isinstance(conditions, dict) or set(conditions) != set(keys):
            raise ValueError(
                "Informe os cenários correspondentes ao caminho escolhido."
            )
        n, base, periods = (
            body.get("n_seeds"),
            body.get("base_seed"),
            body.get("periods"),
        )
        if type(n) is not int or not 1 <= n <= 8:
            raise ValueError("Escolha de 1 a 8 sementes.")
        if type(base) is not int or not 0 <= base <= 1_000_000:
            raise ValueError("A semente inicial deve ficar entre 0 e 1.000.000.")
        if type(periods) is not int or not 1 <= periods <= 80:
            raise ValueError("Escolha de 1 a 80 períodos.")
        seeds = list(range(base, base + n))
        prepared: dict[str, dict[str, Any]] = {}
        for key in keys:
            entry = conditions[key]
            if not isinstance(entry, dict) or not isinstance(entry.get("params"), dict):
                raise ValueError("Confira os parâmetros de cada cenário.")
            params = dict(entry["params"])
            if params.get("microdata_path") is None:
                params.pop("microdata_path", None)
            validate_investigation(params, seeds, periods)
            name = str(entry.get("name") or f"Cenário {key}").strip()
            if len(name) > 100:
                raise ValueError("Use até 100 caracteres no nome do cenário.")
            prepared[key] = {"params": params, "name": name}
        with self.lock:
            if any(item["state"] == "running" for item in self.items.values()):
                raise ValueError(
                    "Há uma execução em andamento. Aguarde ou cancele antes."
                )
            self.counter += 1
            job_id = str(self.counter)
            while len(self.items) >= 4:
                self.items.pop(next(iter(self.items)))
            job = {
                "state": "running",
                "done": 0,
                "total": len(keys) * n,
                "cancel": threading.Event(),
                "result": None,
                "error": None,
            }
            self.items[job_id] = job
        threading.Thread(
            target=self._run,
            args=(job_id, prepared, seeds, periods, mode),
            daemon=True,
        ).start()
        return job_id

    def _run(
        self,
        job_id: str,
        conditions: dict[str, dict[str, Any]],
        seeds: list[int],
        periods: int,
        mode: str,
    ) -> None:
        job = self.items[job_id]
        try:
            results = {}
            for index, (key, entry) in enumerate(conditions.items()):

                def report(done: int, offset: int = index * len(seeds)) -> None:
                    with self.lock:
                        job["done"] = offset + done

                result = run_scenario(
                    entry["params"],
                    seeds,
                    periods,
                    cancel=job["cancel"],
                    progress=report,
                )
                verdicts = _verdicts_for(result)
                results[key] = {
                    **result,
                    **verdicts,
                    "id": f"live-{job_id}-{key}",
                    "name": entry["name"],
                    "description": "Execução personalizada no motor local.",
                    "phenomenon": "Exploração personalizada",
                    "hypothesis": "Exploratória",
                    "reference": "Parâmetros definidos pelo usuário",
                    "provenance": self.metadata,
                    "source": "live",
                }
            with self.lock:
                if job["cancel"].is_set():
                    job["state"] = "cancelled"
                else:
                    job["result"] = {
                        "simulation": True,
                        "notice": "Simulação; não são observações empíricas.",
                        "mode": mode,
                        "seeds": seeds,
                        "periods": periods,
                        "conditions": results,
                    }
                    job["state"] = "done"
        except CancelledError:
            with self.lock:
                job["state"] = "cancelled"
        except Exception as error:
            with self.lock:
                job["error"] = _translate_error(str(error))
                job["state"] = "error"

    def status(self, job_id: str) -> dict[str, Any]:
        with self.lock:
            item = self.items[job_id]
            return {key: value for key, value in item.items() if key != "cancel"}

    def cancel(self, job_id: str) -> None:
        with self.lock:
            self.items[job_id]["cancel"].set()


class WorkbenchServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int, directory: Path) -> None:
        self.directory = directory
        self.page = _page_info(directory)
        self.jobs = Jobs()
        super().__init__(("127.0.0.1", port), Handler)

    def server_close(self) -> None:
        with self.jobs.lock:
            items = list(self.jobs.items.values())
        for item in items:
            item["cancel"].set()
        super().server_close()


class Handler(BaseHTTPRequestHandler):
    def _server(self) -> WorkbenchServer:
        return cast(WorkbenchServer, self.server)

    def _send(self, status: int, payload: Any, *, html: bool = False) -> None:
        raw = (
            payload if html else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        )
        compressed = "gzip" in self.headers.get("Accept-Encoding", "") and not html
        if compressed:
            raw = gzip.compress(raw, mtime=0)
        self.send_response(status)
        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8" if html else "application/json; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        if compressed:
            self.send_header("Content-Encoding", "gzip")
        self.end_headers()
        try:
            for start in range(0, len(raw), 16_384):
                self.wfile.write(raw[start : start + 16_384])
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(
                200, (self._server().directory / "index.html").read_bytes(), html=True
            )
        elif path == "/api/investigation/health":
            self._send(
                200,
                {
                    "available": True,
                    "max_seeds": 8,
                    "max_periods": 80,
                    "workbench_schema": 4,
                    "started_utc": STARTED_UTC,
                    "page": self._server().page,
                    "build": self._server().jobs.metadata,
                },
            )
        elif path.startswith("/api/investigation/jobs/"):
            try:
                self._send(200, self._server().jobs.status(path.rsplit("/", 1)[1]))
            except KeyError:
                self._send(
                    404, {"error": "Execução não encontrada. Execute novamente."}
                )
        else:
            self._send(404, {"error": "Endereço não encontrado."})

    def do_POST(self) -> None:
        try:
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + self.headers.get("Host", ""):
                self._send(403, {"error": "Abra a interface neste servidor local."})
                return
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 65_536:
                raise ValueError(
                    "A configuração enviada é grande demais ou está vazia."
                )
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError("Envie uma configuração válida.")
            if self.path == "/api/investigation/run":
                job_id = self._server().jobs.start(body)
                self._send(202, {"job_id": job_id})
            elif self.path == "/api/investigation/cancel":
                self._server().jobs.cancel(str(body.get("job_id")))
                self._send(200, {"cancelled": True})
            else:
                self._send(404, {"error": "Ação não encontrada."})
        except (ValueError, TypeError, KeyError) as error:
            self._send(400, {"error": _translate_error(str(error))})

    def log_message(self, format: str, *args: Any) -> None:
        del format, args


def create_server(port: int = 8777, directory: Path | None = None) -> WorkbenchServer:
    return WorkbenchServer(port, directory or ROOT / "outputs/investigation")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8777)
    args = parser.parse_args()
    server = create_server(args.port)
    print(f"Workbench: http://127.0.0.1:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

"""Scientific provenance and real browser journey for the optional prototype."""

from __future__ import annotations

import csv
import importlib.util
import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import expect, sync_playwright

from technology_park_abm.investigation import run_scenario
from technology_park_abm.model import TechnologyParkModel
from technology_park_abm.workbench_core import DEMO_PLAYBOOKS, config_from_params

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "investigation_builder", ROOT / "scripts/build_investigation_prototype.py"
)
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)
SERVER_SPEC = importlib.util.spec_from_file_location(
    "investigation_server", ROOT / "scripts/serve_investigation_prototype.py"
)
assert SERVER_SPEC is not None and SERVER_SPEC.loader is not None
SERVER = importlib.util.module_from_spec(SERVER_SPEC)
SERVER_SPEC.loader.exec_module(SERVER)


def use_example(page: Any) -> None:
    if not page.locator("#use-example").is_visible():
        page.get_by_text("Explorar exemplos já calculados", exact=True).click()
    page.locator("#use-example").click()


@pytest.fixture(scope="module")
def prototype(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, Any]]:
    evidence: dict[str, Any] = BUILDER.build_evidence()
    path = tmp_path_factory.mktemp("investigation") / "index.html"
    path.write_text(BUILDER.render_prototype(evidence), encoding="utf-8")
    return path, evidence


def test_paired_evidence_reproduces_and_changes_only_capacity(
    prototype: tuple[Path, dict[str, Any]],
) -> None:
    path, evidence = prototype
    assert BUILDER.build_evidence() == evidence
    conditions = evidence["conditions"]
    a, b = conditions["A"], conditions["B"]
    different = {key for key in a["config"] if a["config"][key] != b["config"][key]}
    assert different == {"infrastructure_capacity"}
    assert [run["seed"] for run in a["runs"]] == list(range(1, 9))
    assert [run["seed"] for run in b["runs"]] == list(range(1, 9))
    for index in range(8):
        assert (
            b["runs"][index]["history"][0]["congestion"]
            < (a["runs"][index]["history"][0]["congestion"])
        )
    # The dashboard's reduced history omits these metrics: check against the
    # original model record so an accidental switch back cannot lose evidence.
    model = TechnologyParkModel(
        config=config_from_params(
            {"seed": 1, "n_startups": 18, "infrastructure_capacity": 8}
        )
    )
    for index, record in enumerate(a["runs"][0]["history"]):
        raw: dict[str, Any] = dict(model.advance())
        assert record == {key: raw[key] for key in record}
        events = a["runs"][0]["events"][index]
        assert events == {key: raw[key] for key in events}
    for horizon in (1, 19, 20, 40, 60, 80):
        assert (
            len(a["maps"][str(horizon)]["nodes"])
            == (a["runs"][0]["history"][horizon - 1]["active_startup_count"])
        )
    assert evidence["simulation"] is True
    assert evidence["source_sha256"]
    assert "__EVIDENCE_JSON__" not in path.read_text(encoding="utf-8")


def test_all_original_scenarios_and_every_network_frame_are_preserved(
    prototype: tuple[Path, dict[str, Any]],
) -> None:
    _, evidence = prototype
    assert len(evidence["scenarios"]) == 11
    for index, playbook in enumerate(DEMO_PLAYBOOKS):
        item = evidence["scenarios"][index]
        assert item["original_name"] == playbook["name"]
        assert item["config"] == asdict(
            config_from_params({**playbook["params"], "seed": 1})
        )
        assert set(item["maps"]) == {str(period) for period in range(81)}
        first = item["runs"][0]
        for period in range(81):
            record = first["initial"] if period == 0 else first["history"][period - 1]
            nodes = item["maps"][str(period)]["nodes"]
            assert (
                sum(node["type"] == "startup" for node in nodes)
                == (record["active_startup_count"])
            )
    full_cast = evidence["scenarios"][8]["maps"]["0"]["nodes"]
    assert {node["type"] for node in full_cast} == {
        "startup",
        "anchor",
        "university",
        "investor",
        "worker",
    }


@pytest.mark.e2e
@pytest.mark.a11y
def test_investigation_journey_and_export(
    prototype: tuple[Path, dict[str, Any]], tmp_path: Path
) -> None:
    path, evidence = prototype
    errors: list[str] = []
    with sync_playwright() as stack:
        browser = stack.chromium.launch()
        page = browser.new_page(accept_downloads=True)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(path.as_uri())
        page.get_by_role("button", name="Preparar uma investigação").click()
        assert page.locator("#title-1").evaluate("el => el === document.activeElement")
        page.locator('[name="investigation-mode"][value="compare"]').check()
        page.locator("#replicates").select_option("8")
        page.locator("#horizon").select_option("20")
        use_example(page)
        page.locator("#go-final").click()
        assert page.locator("#trajectory").get_attribute("data-band") == "p10-p90"
        finals = [run["history"][19] for run in evidence["conditions"]["A"]["runs"]]
        expected = sum(row["productive_tie_count"] for row in finals) / 8
        visible = (
            page.locator("#value-a").inner_text().replace(".", "").replace(",", ".")
        )
        assert float(visible) == pytest.approx(expected, abs=0.051)
        expect(page.locator("#network-scope")).to_contain_text("semente 1")
        assert "undefined" not in page.locator("#network-node").inner_text()
        page.locator("#network-condition").select_option("B")
        page.locator("#metric").select_option("congestion")
        page.get_by_role("button", name="Interpretar e registrar").click()
        assert (
            "A hipótese não é confirmada"
            in page.locator('[data-page="3"]').inner_text()
        )
        with page.expect_download() as downloading:
            page.locator("#export-json").click()
        json_path = tmp_path / "investigation.json"
        downloading.value.save_as(json_path)
        exported = json.loads(json_path.read_text(encoding="utf-8"))
        assert exported["simulation"] is True
        assert exported["seeds"] == list(range(1, 9))
        assert exported["horizon"] == 20
        assert exported["selected_metric"] == "congestion"
        assert exported["source_sha256"] == evidence["source_sha256"]
        for condition in ("A", "B"):
            assert (
                exported["conditions"][condition]["runs"][0]["history"]
                == (evidence["conditions"][condition]["runs"][0]["history"][:20])
            )
        with page.expect_download() as downloading_csv:
            page.locator("#export-csv").click()
        csv_path = tmp_path / "trajectories.csv"
        downloading_csv.value.save_as(csv_path)
        with csv_path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 2 * 8 * 21  # Schema 2 includes the initial p0 row.
        assert {row["condition"] for row in rows} == {"A", "B"}
        assert {row["simulation"] for row in rows} == {"true"}
        page.locator('[data-step="1"]').click()
        page.locator("#replicates").select_option("1")
        use_example(page)
        assert page.locator("#trajectory").get_attribute("data-band") == "none"
        assert "Não há faixa" in page.locator("#uncertainty-reading").inner_text()
        assert errors == []
        browser.close()


@pytest.mark.e2e
@pytest.mark.a11y
@pytest.mark.parametrize(
    ("mode", "threshold_a", "threshold_b"),
    [("compare", 0.0, 1.0), ("compare", 0.5, 0.5), ("observe", 0.7, 0.5)],
)
def test_measurement_definitions_follow_config_and_guard_deltas(
    workbench: Any,
    tmp_path: Path,
    mode: str,
    threshold_a: float,
    threshold_b: float,
) -> None:
    base, server = workbench
    incompatible = mode == "compare" and threshold_a != threshold_b
    with sync_playwright() as stack:
        browser = stack.chromium.launch()
        page = browser.new_page(accept_downloads=True)
        page.goto(base)
        page.get_by_role("button", name="Preparar uma investigação").click()
        if mode == "compare":
            page.locator('[name="investigation-mode"][value="compare"]').check()
            page.locator("#scenario-b").select_option("tour-5")
        for c, threshold in [("a", threshold_a), ("b", threshold_b)][
            : (2 if mode == "compare" else 1)
        ]:
            page.locator(f"#editor-details-{c} > summary").click()
            page.locator(f"#params-editor-{c}").get_by_text(
                "Parâmetros avançados", exact=True
            ).click()
            page.locator(f"#param-{c}-productive_tie_strength_threshold").fill(
                str(threshold)
            )
        if incompatible:
            expect(page.locator("#comparison-warning")).to_contain_text(
                "não a dinâmica da rede"
            )
        page.locator("#seed-base").fill("42")
        page.locator("#replicates").select_option("1")
        page.locator("#horizon").select_option("20")
        page.locator("#run-config").click()
        expect(page.locator('[data-page="2"]')).to_be_visible(timeout=20000)
        page.locator("#go-final").click()
        batch = next(reversed(server.jobs.items.values()))["result"]["conditions"]
        for c in batch:
            item = batch[c]
            ties = item["maps"]["20"]["edges"]
            expected = sum(
                edge["type"] == "partnership"
                and edge["strength"]
                >= item["config"]["productive_tie_strength_threshold"]
                for edge in ties
            )
            assert item["runs"][0]["history"][-1]["productive_tie_count"] == expected
        if incompatible:
            assert batch["A"]["maps"] == batch["B"]["maps"]
            assert page.locator("#value-a").inner_text() == "42,0"
            assert page.locator("#value-b").inner_text() == "0,0"
            expect(page.locator("#metric-unit")).to_contain_text("A: força ≥ 0")
            expect(page.locator("#metric-unit")).to_contain_text("B: força ≥ 1")
            assert page.locator("#value-delta").inner_text() == "—"
            page.locator("#values-panel > summary").click()
            assert (
                page.locator("#values-body tr").first.locator("td").last.inner_text()
                == "—"
            )
            expect(page.locator("#paired-reading")).to_contain_text("não calculada")
            expect(page.locator("#chart-caption")).to_contain_text("não calculada")
            page.locator("#metric").select_option("capital_total")
            assert page.locator("#value-delta").inner_text() == "0,0"
            page.locator("#metric").select_option("productive_tie_count")
            assert page.locator("#value-delta").inner_text() == "—"
        else:
            expected_unit = str(threshold_a).replace(".", ",")
            expect(page.locator("#metric-unit")).to_contain_text(
                f"força ≥ {expected_unit}"
            )
            if mode == "compare":
                assert page.locator("#value-delta").inner_text() == "0,0"
        page.get_by_role("button", name="Interpretar e registrar").click()
        if incompatible:
            expect(page.locator("#conclusion-fact")).to_contain_text("não calculada")
            assert "foi -42" not in page.locator("#conclusion-fact").inner_text()
        with page.expect_download() as downloading:
            page.locator("#export-json").click()
        target = tmp_path / "measurement.json"
        downloading.value.save_as(target)
        exported = json.loads(target.read_text(encoding="utf-8"))
        assert exported["measurement"]["comparable"] is not incompatible
        assert exported["measurement"]["thresholds"]["A"] == threshold_a
        assert Axe().run(page).violations_count == 0
        browser.close()


@pytest.mark.e2e
@pytest.mark.parametrize("mode", ["observe", "compare"])
def test_csv_alone_reproduces_each_condition_seed_and_initial_state(
    workbench: Any, tmp_path: Path, mode: str
) -> None:
    base, server = workbench
    with sync_playwright() as stack:
        browser = stack.chromium.launch()
        page = browser.new_page(accept_downloads=True)
        page.goto(base)
        page.get_by_role("button", name="Preparar uma investigação").click()
        page.locator("#scenario-a").select_option("critical-mass")
        if mode == "compare":
            page.locator('[name="investigation-mode"][value="compare"]').check()
        page.locator("#editor-details-a > summary").click()
        page.locator("#param-a-sectors").fill('bio"tech, energia')
        page.locator("#seed-base").fill("42")
        page.locator("#replicates").select_option("4")
        page.locator("#horizon").select_option("20")
        page.locator("#run-config").click()
        expect(page.locator('[data-page="2"]')).to_be_visible(timeout=20000)
        for period in (0, 11):
            if period:
                page.locator("#step-one").click()
                page.locator("#step-ten").click()
            page.locator('[data-step="3"]').click()
            with page.expect_download() as downloading:
                page.locator("#export-csv").click()
            target = tmp_path / f"{period}.csv"
            downloading.value.save_as(target)
            with target.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            expected_conditions = {"A", "B"} if mode == "compare" else {"A"}
            assert len(rows) == len(expected_conditions) * 4 * (period + 1)
            assert {row["condition"] for row in rows} == expected_conditions
            assert {row["schema"] for row in rows} == {"investigation-trajectories-2"}
            assert {row["simulation"] for row in rows} == {"true"}
            assert {int(row["period"]) for row in rows} == set(range(period + 1))
            assert {int(row["seed"]) for row in rows} == {42, 43, 44, 45}
            for condition in expected_conditions:
                for seed in (42, 43, 44, 45):
                    subset = [
                        row
                        for row in rows
                        if row["condition"] == condition and int(row["seed"]) == seed
                    ]
                    first = subset[0]
                    config = json.loads(first["config_json"])
                    assert config["seed"] == seed
                    if condition == "A":
                        assert config["sectors"] == ['bio"tech', "energia"]
                        assert first["base_scenario_id"] == "critical-mass"
                    provenance = json.loads(first["provenance_json"])
                    assert provenance == server.jobs.metadata
                    assert first["git_commit"] == provenance["git_commit"]
                    assert first["model_version"] == provenance["version"]
                    params = {
                        key: value for key, value in config.items() if key != "policy"
                    }
                    params.update(
                        {f"policy__{k}": v for k, v in config["policy"].items()}
                    )
                    reproduced = run_scenario(params, [seed], max(1, period))["runs"][0]
                    expected = [reproduced["initial"], *reproduced["history"][:period]]
                    for row, record in zip(subset, expected, strict=True):
                        assert int(row["period"]) == record["period"]
                        for metric in BUILDER.METRICS:
                            assert float(row[metric]) == record[metric]
            with page.expect_download() as downloading_again:
                page.locator("#export-csv").click()
            again = tmp_path / "again.csv"
            downloading_again.value.save_as(again)
            assert again.read_bytes() == target.read_bytes()
            page.locator('[data-step="2"]').click()
        browser.close()


@pytest.mark.e2e
def test_transport_error_is_actionable_and_retry_preserves_draft(
    workbench: Any,
) -> None:
    base, _ = workbench
    with sync_playwright() as stack:
        browser = stack.chromium.launch()
        page = browser.new_page()
        page.goto(base)
        page.get_by_role("button", name="Preparar uma investigação").click()
        page.locator("#editor-details-a > summary").click()
        page.locator("#param-a-infrastructure_capacity").fill("13")
        page.locator("#seed-base").fill("42")
        page.locator("#horizon").select_option("20")
        page.locator("#replicates").select_option("1")
        page.route("**/api/investigation/run", lambda route: route.abort("failed"))
        page.locator("#run-config").click()
        expect(page.locator("#run-status")).to_contain_text("tente novamente")
        expect(page.locator("#run-status")).to_contain_text("servidor de investigação")
        assert "Failed to fetch" not in page.locator("#run-status").inner_text()
        expect(page.locator("#run-config")).to_be_enabled()
        assert page.locator("#param-a-infrastructure_capacity").input_value() == "13"
        assert page.locator("#seed-base").input_value() == "42"
        page.unroute("**/api/investigation/run")
        page.locator("#run-config").click()
        expect(page.locator('[data-page="2"]')).to_be_visible(timeout=20000)
        browser.close()


@pytest.mark.e2e
@pytest.mark.a11y
def test_figure_carries_scope_and_mobile_reading_has_16px_floor(
    prototype: tuple[Path, dict[str, Any]],
) -> None:
    path, _ = prototype
    with sync_playwright() as stack:
        browser = stack.chromium.launch()
        page = browser.new_page()
        for mode in ("observe", "compare"):
            for n in (1, 4):
                page.goto(path.as_uri())
                page.get_by_role("button", name="Preparar uma investigação").click()
                if mode == "compare":
                    page.locator('[name="investigation-mode"][value="compare"]').check()
                page.locator("#replicates").select_option(str(n))
                page.locator("#horizon").select_option("20")
                use_example(page)
                page.locator("#step-ten").click()
                figure = page.locator('figure[aria-labelledby="metric-heading"]')
                expect(figure.locator("#figure-scope")).to_contain_text("Simulação")
                expect(figure.locator("#figure-scope")).to_contain_text(
                    "período visível 10 de 20"
                )
                expect(figure.locator("#figure-scope")).to_contain_text(
                    "sementes " + ", ".join(str(seed) for seed in range(1, n + 1))
                )
                expect(figure.locator("#figure-scope")).to_contain_text(
                    f"{n} pares A/B" if mode == "compare" else f"{n} execuções"
                )
                expect(figure.locator("#metric-unit")).to_contain_text("força ≥ 0,5")
                assert figure.locator("#condition-label-a").inner_text()
                for width in (320, 360, 412):
                    page.set_viewport_size({"width": width, "height": 915})
                    assert (
                        page.evaluate("document.documentElement.scrollWidth") <= width
                    )
                    for selector in (
                        "#figure-scope",
                        "#metric-unit",
                        "#network-scope",
                        "#chart-caption",
                    ):
                        assert (
                            page.locator(selector).evaluate(
                                "el => parseFloat(getComputedStyle(el).fontSize)"
                            )
                            >= 16
                        )
                assert Axe().run(page).violations_count == 0
        page.locator('[data-step="0"]').click()
        assert (
            page.locator('[data-page="0"] .small.section-gap').evaluate(
                "el => parseFloat(getComputedStyle(el).fontSize)"
            )
            >= 16
        )
        browser.close()


@pytest.mark.e2e
@pytest.mark.a11y
def test_scenario_playback_pause_rewind_and_process_events(
    prototype: tuple[Path, dict[str, Any]],
) -> None:
    path, evidence = prototype
    with sync_playwright() as stack:
        browser = stack.chromium.launch()
        page = browser.new_page(reduced_motion="reduce")
        page.goto(path.as_uri())
        page.locator('[data-step="1"]').click()
        page.locator('[name="investigation-mode"][value="compare"]').check()
        assert page.locator("#scenario-a option").count() == 11
        page.locator("#scenario-a").select_option("tour-6")
        assert "não isola" in page.locator("#comparison-warning").inner_text()
        use_example(page)
        assert page.locator("#network").get_attribute("data-period") == "0"
        page.locator("#step-one").click()
        assert page.locator("#network").get_attribute("data-period") == "1"
        assert page.locator("#trajectory").get_attribute("data-period") == "1"
        page.locator("#step-ten").click()
        assert page.locator("#timeline").input_value() == "11"
        page.locator("#timeline").fill("20")
        expect(page.locator("#period-events")).to_contain_text("choque")
        event = evidence["scenarios"][5]["runs"][0]["events"][19]
        assert f"{event['entry_count']} entrada" in (
            page.locator("#period-events").inner_text()
        )
        page.locator("#rewind").click()
        assert page.locator("#timeline").input_value() == "0"
        page.locator("#play-pause").click()
        page.wait_for_function("Number(document.getElementById('timeline').value) >= 1")
        page.locator("#play-pause").click()
        assert page.locator("#play-pause").get_attribute("aria-pressed") == "false"
        stopped = page.locator("#timeline").input_value()
        page.wait_for_timeout(700)
        assert page.locator("#timeline").input_value() == stopped
        page.locator('[data-step="1"]').click()
        page.locator("#scenario-a").select_option("tour-9")
        use_example(page)
        options = page.locator("#network-node").inner_text()
        assert all(
            word in options for word in ("âncora", "trabalhador", "universidade")
        )
        assert "execução individual" in page.locator("#network-scope").inner_text()
        browser.close()


@pytest.mark.e2e
@pytest.mark.a11y
def test_prototype_accessibility_and_reflow(
    prototype: tuple[Path, dict[str, Any]],
) -> None:
    path, _ = prototype
    with sync_playwright() as stack:
        browser = stack.chromium.launch()
        page = browser.new_page(reduced_motion="reduce")
        page.goto(path.as_uri())
        page.keyboard.press("Tab")
        assert page.locator(".skip").evaluate("el => el === document.activeElement")
        for width in (1440, 320, 360, 412):
            page.set_viewport_size({"width": width, "height": 915})
            for step in range(4):
                if step == 2:
                    use_example(page)
                page.locator(f'[data-step="{step}"]').click()
                assert page.locator(f'[data-page="{step}"]').is_visible()
                assert page.evaluate("document.documentElement.scrollWidth") <= width
                if width == 412 and step == 0:
                    action = page.locator(
                        '[data-page="0"] [data-next="1"]'
                    ).bounding_box()
                    assert action is not None
                    assert action["y"] + action["height"] <= 915
                assert Axe().run(page).violations_count == 0
                assert page.locator("button:visible").evaluate_all(
                    "nodes => nodes.every("
                    "el => el.getBoundingClientRect().height >= 44)"
                )
        browser.close()


@pytest.fixture()
def workbench(prototype: tuple[Path, dict[str, Any]]) -> Any:
    path, _ = prototype
    server = SERVER.create_server(port=0, directory=path.parent)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}", server
    server.shutdown()
    server.server_close()


def api(base: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        result: dict[str, Any] = json.loads(response.read())
        return result


def wait_job(base: str, job_id: str) -> dict[str, Any]:
    end = time.monotonic() + 15
    while time.monotonic() < end:
        job = api(base, "/api/investigation/jobs/" + job_id)
        if job["state"] != "running":
            return job
        time.sleep(0.02)
    raise AssertionError("The bounded model job did not complete")


@pytest.mark.e2e
def test_custom_motor_runs_are_deterministic_and_seed_paired(workbench: Any) -> None:
    base, _ = workbench
    params = {
        "n_startups": 3,
        "infrastructure_capacity": 9,
        "entry_potential_per_period": 0,
    }
    body = {
        "mode": "compare",
        "n_seeds": 2,
        "base_seed": 23,
        "periods": 4,
        "conditions": {
            "A": {"params": params},
            "B": {"params": {**params, "infrastructure_capacity": 12}},
        },
    }
    started = api(base, "/api/investigation/run", body)
    result = wait_job(base, started["job_id"])
    assert result["state"] == "done"
    batch = result["result"]
    assert batch["seeds"] == [23, 24]
    a, b = batch["conditions"]["A"], batch["conditions"]["B"]
    assert a["config"]["infrastructure_capacity"] == 9
    assert b["config"]["infrastructure_capacity"] == 12
    assert (
        a["runs"][0]["history"] == run_scenario(params, [23], 4)["runs"][0]["history"]
    )
    assert [run["seed"] for run in b["runs"]] == [23, 24]
    assert a["source"] == "live" and a["provenance"]["source_sha256"]
    assert set(a["maps"]) == {"0", "1", "2", "3", "4"}
    repeated = api(base, "/api/investigation/run", body)
    again = wait_job(base, repeated["job_id"])["result"]["conditions"]["A"]
    assert again["runs"] == a["runs"] and again["maps"] == a["maps"]


@pytest.mark.e2e
def test_custom_jobs_validate_cancel_and_keep_partial_results_hidden(
    workbench: Any,
) -> None:
    base, _ = workbench
    invalid: dict[str, Any] = {
        "mode": "observe",
        "n_seeds": 9,
        "base_seed": 1,
        "periods": 20,
        "conditions": {"A": {"params": {}}},
    }
    with pytest.raises(urllib.error.HTTPError) as rejected:
        api(base, "/api/investigation/run", invalid)
    assert rejected.value.code == 400
    body = {**invalid, "n_seeds": 8, "periods": 80}
    job = api(base, "/api/investigation/run", body)
    api(base, "/api/investigation/cancel", {"job_id": job["job_id"]})
    cancelled = wait_job(base, job["job_id"])
    assert cancelled["state"] == "cancelled" and cancelled["result"] is None
    with pytest.raises(ValueError):
        run_scenario({"initial_capital": "NaN"}, [1], 1)
    with pytest.raises(ValueError):
        run_scenario({"partnership_attempts_per_startup": 1000}, [1], 1)


@pytest.mark.e2e
@pytest.mark.a11y
def test_observe_mode_customization_and_export_use_new_motor_results(
    workbench: Any, tmp_path: Path
) -> None:
    base, _ = workbench
    with sync_playwright() as stack:
        browser = stack.chromium.launch()
        page = browser.new_page(accept_downloads=True, reduced_motion="reduce")
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base)
        page.get_by_role("button", name="Preparar uma investigação").click()
        assert page.locator('[value="observe"][name="investigation-mode"]').is_checked()
        assert not page.locator("#scenario-b").is_visible()
        expect(page.locator("#scenario-description-a")).to_contain_text(
            "informação para leitura"
        )
        page.locator("#editor-details-a > summary").click()
        page.locator("#param-a-infrastructure_capacity").fill("13")
        page.locator("#replicates").select_option("1")
        page.locator("#horizon").select_option("20")
        page.locator("#seed-base").fill("42")
        page.locator("#run-config").click()
        expect(page.locator('[data-page="2"]')).to_be_visible(timeout=20000)
        page.locator("#go-final").click()
        assert not page.locator("#value-b").is_visible()
        assert "B − A" not in page.locator("#chart-caption").inner_text()
        assert "42" in page.locator("#network-scope").inner_text()
        page.get_by_role("button", name="Interpretar e registrar").click()
        with page.expect_download() as downloading:
            page.locator("#export-json").click()
        target = tmp_path / "custom.json"
        downloading.value.save_as(target)
        result = json.loads(target.read_text(encoding="utf-8"))
        assert result["mode"] == "observe" and set(result["conditions"]) == {"A"}
        assert result["conditions"]["A"]["config"]["infrastructure_capacity"] == 13
        assert result["conditions"]["A"]["source"] == "live"
        assert result["seeds"] == [42] and result["horizon"] == 20
        # A new draft must not render old, shorter or differently seeded runs.
        page.locator('[data-step="1"]').click()
        page.locator("#replicates").select_option("8")
        page.locator("#horizon").select_option("80")
        page.locator('[name="investigation-mode"][value="compare"]').check()
        page.locator('[data-step="2"]').click()
        assert page.locator('[data-page="1"]').is_visible()
        expect(page.locator("#status")).to_contain_text("execute")
        assert errors == []
        assert Axe().run(page).violations_count == 0
        browser.close()


@pytest.mark.e2e
@pytest.mark.a11y
def test_compare_mode_customizes_only_b_and_preserves_a(
    workbench: Any, tmp_path: Path
) -> None:
    base, _ = workbench
    with sync_playwright() as stack:
        browser = stack.chromium.launch()
        page = browser.new_page(accept_downloads=True, reduced_motion="reduce")
        page.goto(base)
        page.get_by_role("button", name="Preparar uma investigação").click()
        page.locator('[name="investigation-mode"][value="compare"]').check()
        page.locator("#editor-details-b > summary").click()
        page.locator("#param-b-infrastructure_capacity").fill("17")
        page.locator("#replicates").select_option("1")
        page.locator("#horizon").select_option("20")
        page.locator("#seed-base").fill("7")
        page.locator("#run-config").click()
        expect(page.locator('[data-page="2"]')).to_be_visible(timeout=20000)
        assert page.locator("#value-b").is_visible()
        page.locator("#go-final").click()
        page.get_by_role("button", name="Interpretar e registrar").click()
        with page.expect_download() as downloading:
            page.locator("#export-json").click()
        path = tmp_path / "compare.json"
        downloading.value.save_as(path)
        result = json.loads(path.read_text(encoding="utf-8"))
        assert result["mode"] == "compare" and set(result["conditions"]) == {"A", "B"}
        assert result["conditions"]["A"]["config"]["infrastructure_capacity"] == 8
        assert result["conditions"]["B"]["config"]["infrastructure_capacity"] == 17
        assert result["changed_parameters"] == ["infrastructure_capacity"]
        assert result["seeds"] == [7]
        assert Axe().run(page).violations_count == 0
        browser.close()


def test_research_designs_use_supported_mechanisms_and_preserve_originals(
    prototype: tuple[Path, dict[str, Any]],
) -> None:
    _, evidence = prototype
    research = evidence["research"]
    assert set(research["order"]) == {item["id"] for item in evidence["scenarios"]}
    for item in evidence["scenarios"]:
        dossier = item["research"]
        assert set(dossier["sources"]) <= set(research["sources"])
        # Each suggested contrast must survive the canonical model parser and
        # produce actual finite trajectories; literature never supplies outcomes.
        params = {
            key: value for key, value in item["config"].items() if key != "policy"
        }
        params.update(
            {"policy__" + key: value for key, value in item["config"]["policy"].items()}
        )
        for arm in ("a", "b"):
            computed = run_scenario({**params, **dossier["contrast"][arm]}, [17], 3)
            assert len(computed["runs"][0]["history"]) == 3
        for key in dossier["sources"]:
            source = research["sources"][key]
            assert source["url"].startswith("https://")
            assert source["application"] and source["access"]
    mass = next(item for item in evidence["scenarios"] if item["id"] == "critical-mass")
    assert mass["config"]["n_startups"] == 8
    assert mass["config"]["entry_potential_per_period"] == 0
    assert mass["config"]["infrastructure_capacity"] == 64
    assert set(mass["maps"]) == {str(period) for period in range(81)}
    assert all(row["congestion"] <= 1 for run in mass["runs"] for row in run["history"])


@pytest.mark.e2e
@pytest.mark.a11y
def test_research_dossier_prepares_a_reviewable_contrast_and_exports_sources(
    workbench: Any, tmp_path: Path
) -> None:
    base, server = workbench
    with sync_playwright() as stack:
        browser = stack.chromium.launch()
        page = browser.new_page(accept_downloads=True, reduced_motion="reduce")
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base)
        page.get_by_role("button", name="Preparar uma investigação").click()
        page.locator("#scenario-a").select_option("critical-mass")
        box = page.locator("#scenario-description-a")
        box.get_by_text("Base conceitual e hipótese", exact=True).click()
        expect(box).to_contain_text("Quando a expectativa não se sustenta")
        expect(box).to_contain_text("Aula 8")
        box.get_by_text(
            "Bettencourt et al. (2007) · Estudo empírico de sistemas urbanos",
            exact=True,
        ).click()
        expect(box).to_contain_text("seus expoentes não podem ser transferidos")
        assert (
            box.get_by_role("link", name="Consultar a obra: Bettencourt").count() == 1
        )
        assert Axe().run(page).violations_count == 0
        box.get_by_role("button", name="Preparar comparação deste roteiro").click()
        assert server.jobs.items == {}  # Preparing must never run the model.
        assert page.locator('[value="compare"][name="investigation-mode"]').is_checked()
        assert page.locator("#scenario-b").input_value() == "critical-mass"
        assert page.locator("#parameter-differences tr").count() == 1
        expect(page.locator("#parameter-differences")).to_contain_text(
            "Startups iniciais"
        )
        page.locator("#replicates").select_option("1")
        page.locator("#horizon").select_option("20")
        page.locator("#run-config").click()
        expect(page.locator('[data-page="2"]')).to_be_visible(timeout=20000)
        page.get_by_role("button", name="Interpretar e registrar").click()
        with page.expect_download() as downloading:
            page.locator("#export-json").click()
        path = tmp_path / "research.json"
        downloading.value.save_as(path)
        exported = json.loads(path.read_text(encoding="utf-8"))
        assert exported["changed_parameters"] == ["n_startups"]
        assert exported["conditions"]["A"]["config"]["n_startups"] == 8
        assert exported["conditions"]["B"]["config"]["n_startups"] == 16
        reference = exported["conditions"]["B"]["research"]
        assert reference["base_scenario_id"] == "critical-mass"
        assert reference["parameters_modified"] is True
        assert "bettencourt2007" in reference["sources"]
        assert reference["dossier"]["contrast"]["b"] == {"n_startups": 16}
        assert errors == []
        browser.close()


def test_workbench_verdicts_are_deterministic_and_honest() -> None:
    """Wave 1: Síntese + Mann-Kendall sobre a média entre sementes."""
    from technology_park_abm.workbench_core import (
        SERIES_LABELS,
        series_verdicts,
        synthesis_block,
    )

    history = [
        {
            "period": period,
            "active_startup_count": 10.0 + period,
            "productive_tie_count": 4.0 + 0.5 * period,
            "knowledge_mean": 1.0 + 0.05 * period,
            "innovation_cumulative": float(period),
            "capital_total": 1000.0 - 10.0 * period,
            "congestion": 0.4 + 0.05 * period,
        }
        for period in range(21)
    ]
    first = (
        synthesis_block(history, config_from_params({"seed": 1})),
        series_verdicts(history),
    )
    second = (
        synthesis_block(history, config_from_params({"seed": 1})),
        series_verdicts(history),
    )
    assert first == second
    synthesis, verdicts = first
    assert synthesis["verdict"].startswith("Popula")
    assert "expans" in synthesis["verdict"]
    assert synthesis["severity"] == "warn"  # congestion crosses 1 in this fixture
    assert "saturada" in (synthesis["alert"] or "")
    assert len(synthesis["trends"]) == 3
    assert synthesis["trends"][0]["label"] == SERIES_LABELS["active_startup_count"]
    assert "crescente" in synthesis["trends"][0]["text"]
    assert "p=" in synthesis["trends"][0]["text"]


def test_workbench_verdicts_withhold_short_series_and_flag_saturation() -> None:
    """Séries curtas não recebem veredito; congestão > 1 vira alerta."""
    from technology_park_abm.workbench_core import (
        SERIES_LABELS,
        series_verdicts,
        synthesis_block,
    )

    short = [{"period": period, "active_startup_count": 10.0} for period in range(3)]
    verdicts = series_verdicts(short)
    assert "série curta (3 períodos)" in verdicts["active_startup_count"]
    assert "sem veredito" in verdicts["capital_total"]

    saturated = [
        {
            "period": period,
            "active_startup_count": 14.0,
            "productive_tie_count": 4.0,
            "knowledge_mean": 1.4,
            "innovation_cumulative": float(period),
            "capital_total": 900.0,
            "congestion": 1.5,
        }
        for period in range(10)
    ]
    synthesis = synthesis_block(saturated, config_from_params({"seed": 1}))
    assert synthesis["severity"] == "warn"
    assert "saturada" in (synthesis["alert"] or "")
    assert "saturação (1,0)" in series_verdicts(saturated)["congestion"]
    assert SERIES_LABELS["knowledge_mean"] == "conhecimento médio"

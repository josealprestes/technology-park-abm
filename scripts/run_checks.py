#!/usr/bin/env python3
"""Verificacao local do technology-park-abm -- substitui o CI que rodava no GitHub.

Contexto: os workflows .github/workflows/ci.yml e mutation.yml e o
.github/dependabot.yml
foram removidos em 2026-10-20 a pedido do autor ("sem CI no GitHub; o que precisar, que
rode localmente"). Este script roda a MESMA bateria na maquina.

Uso:
    python scripts/run_checks.py          # rapido: lint + format + tipos + testes
    python scripts/run_checks.py --fast   # so lint, format e tipos (segundos)
    python scripts/run_checks.py --full     # + mutation testing (mutmut)

Tipos (ADR 0013): mypy --strict continua o gate G3; ty e pyrefly sao
checadores adicionais que rodam logo depois do mypy.

Exit 0 = tudo verde. Cada etapa roda mesmo que a anterior falhe, e o resumo final
diz o que quebrou -- um CI que para na primeira falha esconde as outras.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# A matriz do CI cobria Python 3.12, 3.13 e 3.14. Localmente roda a venv;
# o resumo informa qual foi, para nao dar a impressao falsa de que a matriz foi coberta.
VERSAO_MATRIZ = ("3.12", "3.13", "3.14")


class Resultado:
    def __init__(self, nome: str, rc: int, segundos: float, saída: str) -> None:
        self.nome = nome
        self.rc = rc
        self.segundos = segundos
        self.saída = saída

    @property
    def ok(self) -> bool:
        return self.rc == 0


def rodar(nome: str, comando: list[str], *, timeout: int = 1800) -> Resultado:
    print(f"\n=== {nome} ===", flush=True)
    print(f"$ {' '.join(comando)}", flush=True)
    início = time.monotonic()
    try:
        proc = subprocess.run(
            comando,
            cwd=RAIZ,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        rc = proc.returncode
        saída = (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        rc = 124
        saída = f"timeout de {timeout}s excedido"
    except FileNotFoundError:
        rc = 127
        saída = f"comando nao encontrado: {comando[0]}"
    segundos = time.monotonic() - início

    # mostra a cauda: suficiente para diagnosticar, sem inundar o terminal
    linhas = [ln for ln in saída.strip().splitlines() if ln.strip()]
    for ln in linhas[-25:]:
        print(f"  {ln}")
    if len(linhas) > 25:
        print(f"  ... ({len(linhas) - 25} linhas omitidas)")
    print(
        f"[{'OK' if rc == 0 else 'FAIL'}] {nome} ({segundos:.1f}s, rc={rc})", flush=True
    )
    return Resultado(nome, rc, segundos, saída)


def chromium_instalado() -> bool:
    """Os testes de a11y (gate G12) precisam do Chromium do Playwright.

    No Windows o browser costuma ter sido instalado por OUTRO usuario (o dashboard roda
    numa venv criada na sessao do autor, enquanto o Playwright foi instalado na conta de
    uso). Sem procurar os perfis de `C:/Users/*`, o runner reporta "nao encontrado" e
    silencia a suite inteira -- o mesmo defeito de silencio que corrigimos no mapa.
    """
    padroes: list[Path] = [
        Path.home() / "AppData/Local/ms-playwright",
        Path.home() / ".cache/ms-playwright",
    ]
    padroes += sorted(Path("C:/Users").glob("*/AppData/Local/ms-playwright"))
    env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if env:
        padroes.insert(0, Path(env))

    encontrado = next(
        (p for p in padroes if p.exists() and any(p.glob("chromium*"))), None
    )
    if encontrado is None:
        return False
    if not env:
        # Aponta o Playwright para o browser encontrado, para a suite rodar sem que o
        # operador precise lembrar da variavel.
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(encontrado)
        print("Chromium encontrado; PLAYWRIGHT_BROWSERS_PATH ajustado")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="inclui mutation testing")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="so lint, format e checagem de tipos (mypy + ty + pyrefly)",
    )
    args = parser.parse_args()

    python = sys.executable
    resultados: list[Resultado] = []

    print("=" * 62)
    print("Verificacao local do technology-park-abm")
    print(f"Python {sys.version.split()[0]}  (o CI cobria: {', '.join(VERSAO_MATRIZ)})")
    if not chromium_instalado():
        print(
            "AVISO: Chromium do Playwright nao encontrado -- os testes de a11y serao\n"
            "       pulados. Para habilitar: python -m playwright install chromium\n"
            "       (ou defina PLAYWRIGHT_BROWSERS_PATH)."
        )
    print("=" * 62)

    # 1-5: estaticos (sempre)
    resultados.append(
        rodar("Lint (ruff check)", [python, "-m", "ruff", "check", "."], timeout=300)
    )
    resultados.append(
        rodar(
            "Format (ruff format --check)",
            [python, "-m", "ruff", "format", "--check", "."],
            timeout=300,
        )
    )
    resultados.append(rodar("Type check (mypy)", [python, "-m", "mypy"], timeout=600))
    resultados.append(
        rodar(
            "Type check (ty)",
            [python, "-m", "ty", "check", "src", "tests", "scripts"],
            timeout=600,
        )
    )
    resultados.append(
        rodar(
            "Type check (pyrefly)",
            [python, "-m", "pyrefly", "check", "src", "tests", "scripts"],
            timeout=600,
        )
    )

    if not args.fast:
        # 4: testes completos, tratando warnings como erro (como no CI)
        resultados.append(
            rodar(
                "Testes (pytest + cobertura)",
                [
                    python,
                    "-m",
                    "pytest",
                    "-q",
                    "-W",
                    "error::DeprecationWarning",
                    "-W",
                    "error::FutureWarning",
                    "--cov",
                    "--cov-report=term-missing",
                ],
                timeout=2400,
            )
        )

        # 5: smoke do pacote (o modelo roda fim a fim)
        resultados.append(
            rodar("Smoke run", [python, "-m", "technology_park_abm"], timeout=600)
        )

        # 6-7: smokes de experimento e sensibilidade, em diretorio temporario
        with tempfile.TemporaryDirectory(prefix="tpa_checks_") as tmp:
            resultados.append(
                rodar(
                    "Experiment smoke (E5, 1 seed, 3 períodos)",
                    [
                        python,
                        "-m",
                        "technology_park_abm.experiments",
                        "E5",
                        "--seeds",
                        "1",
                        "--periods",
                        "3",
                        "--output",
                        f"{tmp}/ci",
                    ],
                    timeout=900,
                )
            )
            resultados.append(
                rodar(
                    "Sensitivity smoke (1 seed, 3 períodos)",
                    [
                        python,
                        "-m",
                        "technology_park_abm.sensitivity",
                        "--seeds",
                        "1",
                        "--periods",
                        "3",
                        "--output",
                        f"{tmp}/ci/sensitivity.json",
                    ],
                    timeout=900,
                )
            )

        # 8: política de dados -- nada de dado bruto ou resultado versionado
        print(
            "\n=== Política de dados (nada de data/raw, data/processed, "
            "results no git) ==="
        )
        git = shutil.which("git")
        if git is None:
            print("  git nao encontrado -- etapa pulada")
        else:
            proc = subprocess.run(
                [git, "ls-files", "data/raw", "data/processed", "results"],
                cwd=RAIZ,
                capture_output=True,
                text=True,
                check=False,
            )
            rastreados = [ln for ln in proc.stdout.splitlines() if ln.strip()]
            if rastreados:
                print("  VIOLACAO: arquivos versionados que nao deveriam estar no git:")
                for ln in rastreados[:20]:
                    print(f"    {ln}")
                resultados.append(
                    Resultado("Política de dados", 1, 0.0, "\n".join(rastreados))
                )
            else:
                print("  nenhum arquivo proibido versionado")
                resultados.append(Resultado("Política de dados", 0, 0.0, ""))

    if args.full:
        resultados.append(
            rodar(
                "Mutation testing (mutmut)",
                [python, "-m", "mutmut", "run"],
                timeout=7200,
            )
        )
        if (RAIZ / "mutants").exists():
            resultados.append(
                rodar(
                    "Mutation results", [python, "-m", "mutmut", "results"], timeout=300
                )
            )

    # ---------------- resumo ----------------
    falhas = [r for r in resultados if not r.ok]
    print("\n" + "=" * 62)
    for r in resultados:
        marca = "OK  " if r.ok else "FAIL"
        print(f"  [{marca}] {r.nome}  ({r.segundos:.1f}s)")
    print("=" * 62)

    if not falhas:
        print("TUDO VERDE")
        return 0

    print(
        f"VERMELHO: {len(falhas)} etapa(s) falharam -> "
        f"{', '.join(r.nome for r in falhas)}"
    )
    print("\nDetalhe das falhas:")
    for r in falhas:
        print(f"\n--- {r.nome} (rc={r.rc}) ---")
        linhas = [ln for ln in r.saída.strip().splitlines() if ln.strip()]
        for ln in linhas[-40:]:
            print(f"  {ln}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

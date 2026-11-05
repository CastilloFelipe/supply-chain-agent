"""Arma reporte.md a partir de una narrativa escrita fuera del programa (p.ej. por Claude Code).

    python scripts/componer_reporte.py outputs/20261105-120000

Lee escenario.json y narrativa.md de esa carpeta y escribe reporte.md, con la
tabla de cifras generada en codigo (igual que el modo con API).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from whatif_agent.report import compose_report  # noqa: E402


def main() -> None:
    out = Path(sys.argv[1])
    saved = json.loads((out / "escenario.json").read_text(encoding="utf-8"))
    narrative = (out / "narrativa.md").read_text(encoding="utf-8")
    report = compose_report(saved["escenario"]["question"], narrative, saved["comparacion"], saved["unidades"])
    (out / "reporte.md").write_text(report, encoding="utf-8")
    print(f"Escrito {out / 'reporte.md'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from rag_adm.evaluation import evaluate_modes, render_markdown_report  # noqa: E402


def main() -> int:
    base_path = REPO_ROOT
    dataset_path = base_path / "tests" / "golden_dataset_adm.json"
    report_path = base_path / "docs" / "reporte_calidad_retrievers.md"
    json_path = base_path / "docs" / "reporte_calidad_retrievers.json"

    metrics, raw_results = evaluate_modes(base_path, dataset_path)

    report_markdown = render_markdown_report(metrics)
    report_path.write_text(report_markdown + "\n", encoding="utf-8")

    payload = {
        "metrics": [
            {
                "mode": entry.mode,
                "total_cases": entry.total_cases,
                "role_accuracy": entry.role_accuracy,
                "permission_coverage": entry.permission_coverage,
                "confidence_stability": entry.confidence_stability,
            }
            for entry in metrics
        ],
        "raw_results": raw_results,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Reporte markdown generado en: {report_path}")
    print(f"Reporte json generado en: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

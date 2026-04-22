from __future__ import annotations

from pathlib import Path

from rag_adm.evaluation import evaluate_modes, render_markdown_report


def test_quality_metrics_compare_all_retrievers() -> None:
    base_path = Path(__file__).resolve().parents[1]
    dataset_path = base_path / "tests" / "golden_dataset_adm.json"

    metrics, _ = evaluate_modes(base_path, dataset_path)
    by_mode = {entry.mode: entry for entry in metrics}

    assert set(by_mode.keys()) == {"jaccard", "vector", "hybrid"}

    for mode in ("jaccard", "vector", "hybrid"):
        entry = by_mode[mode]
        assert entry.total_cases >= 10
        assert 0.0 <= entry.role_accuracy <= 1.0
        assert 0.0 <= entry.permission_coverage <= 1.0
        assert 0.0 <= entry.confidence_stability <= 1.0

    # Guardrails de calidad mínima para dataset dorado ADM
    assert by_mode["jaccard"].role_accuracy >= 0.80
    assert by_mode["vector"].role_accuracy >= 0.80
    assert by_mode["hybrid"].role_accuracy >= 0.80

    # El enfoque híbrido no debe degradar cobertura frente a modos base
    assert by_mode["hybrid"].permission_coverage >= by_mode["jaccard"].permission_coverage - 0.05
    assert by_mode["hybrid"].permission_coverage >= by_mode["vector"].permission_coverage - 0.05


def test_quality_report_render_contains_all_modes() -> None:
    base_path = Path(__file__).resolve().parents[1]
    dataset_path = base_path / "tests" / "golden_dataset_adm.json"

    metrics, _ = evaluate_modes(base_path, dataset_path)
    report = render_markdown_report(metrics)

    assert "jaccard" in report
    assert "vector" in report
    assert "hybrid" in report
    assert "Precision Rol" in report
    assert "Cobertura Permisos" in report
    assert "Estabilidad Confianza" in report

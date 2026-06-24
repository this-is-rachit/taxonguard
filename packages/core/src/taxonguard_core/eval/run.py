"""Run the full evaluation: report, results JSON, and a figure.

Builds the labeled benchmark, scores it with the pre-calibration weights and the
calibrated weights, prints a comparison, writes a results JSON, and renders a
two-panel figure (the ROC curve and the suspicion-score distribution by
category). The figure step imports matplotlib lazily and is skipped with a note
if it is not installed, so the core evaluation never depends on a plotting
library.

    uv run python -m taxonguard_core.eval.run
    uv run python -m taxonguard_core.eval.run --seed 0 --output-dir docs
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..engine.fusion import FusionWeights
from ..explain.cluster import DEFAULT_MIN_SCORE
from .benchmark import benchmark_label_counts, build_benchmark
from .calibrate import calibrate, f1_at_threshold_objective
from .metrics import (
    average_precision,
    best_f1,
    metrics_at,
    recall_at_max_fpr,
    roc_auc,
    roc_curve,
)
from .scoring import (
    fuse_prepared,
    labels_are_suspicious,
    prepare_benchmark,
    suspicion_scores,
)

# The pre-calibration weights (the environmental weight before Phase 7 raised it).
STARTING_WEIGHTS = FusionWeights(environmental=0.8)

# Planted error types, in reporting order.
ERROR_TYPES: tuple[str, ...] = (
    "ocean",
    "null_island",
    "equal",
    "gridded",
    "institution",
    "climate",
)

# False positive rate caps reported as product-relevant operating points.
FPR_CAPS: tuple[float, ...] = (0.01, 0.02, 0.05)


def per_type_recall(frame: pd.DataFrame, scores: np.ndarray, threshold: float) -> dict[str, float]:
    """Fraction of each planted error type caught at the threshold."""
    flagged = scores >= threshold
    out: dict[str, float] = {}
    for kind in ERROR_TYPES:
        mask = (frame["error_type"] == kind).to_numpy(dtype=bool)
        total = int(mask.sum())
        out[kind] = float(np.sum(flagged & mask) / total) if total else float("nan")
    return out


def evaluate(frame: pd.DataFrame, threshold: float) -> dict[str, Any]:
    """Metrics for an already-fused frame at the operating threshold."""
    scores = suspicion_scores(frame)
    y = labels_are_suspicious(frame)
    at_threshold = metrics_at(scores, y, threshold)
    caps = {
        f"recall_at_fpr_{int(cap * 100)}pct": recall_at_max_fpr(scores, y, cap).recall
        for cap in FPR_CAPS
    }
    return {
        "operating_threshold": threshold,
        "roc_auc": roc_auc(scores, y),
        "average_precision": average_precision(scores, y),
        "best_f1": best_f1(scores, y).as_dict(),
        "at_operating_threshold": at_threshold.as_dict(),
        "recall_at_fpr_caps": caps,
        "per_type_recall_at_threshold": per_type_recall(frame, scores, threshold),
    }


def build_report(seed: int, threshold: float, grid_steps: int) -> dict[str, Any]:
    """Run the whole evaluation and return a structured report."""
    cases = build_benchmark(seed)
    prepared = prepare_benchmark(cases)

    starting_frame = fuse_prepared(prepared, STARTING_WEIGHTS)
    calibration = calibrate(
        prepared,
        objective=f1_at_threshold_objective(threshold),
        objective_name=f"f1@{threshold:g}",
        start=STARTING_WEIGHTS,
        grid_steps=grid_steps,
    )
    calibrated_frame = fuse_prepared(prepared, calibration.weights)

    return {
        "seed": seed,
        "benchmark": {
            "label_counts": benchmark_label_counts(cases),
            "cases": [case.name for case in cases],
            "errors_per_type_per_case": int((cases[0].frame["error_type"] == "climate").sum()),
        },
        "calibration": {
            "objective": calibration.objective_name,
            "baseline_value": calibration.baseline_value,
            "calibrated_value": calibration.objective_value,
            "improvement": calibration.improvement,
            "starting_weights": vars(STARTING_WEIGHTS),
            "calibrated_weights": vars(calibration.weights),
        },
        "starting": evaluate(starting_frame, threshold),
        "calibrated": evaluate(calibrated_frame, threshold),
    }


def _format_report(report: dict[str, Any]) -> str:
    counts = report["benchmark"]["label_counts"]
    cal = report["calibration"]
    start = report["starting"]
    calib = report["calibrated"]
    lines = [
        "TaxonGuard evaluation",
        "=====================",
        f"benchmark: {counts['total']} records "
        f"({counts['plausible']} plausible, {counts['suspicious']} planted errors) "
        f"across {len(report['benchmark']['cases'])} taxa, seed {report['seed']}",
        "",
        "ranking quality (calibrated weights):",
        f"  ROC-AUC = {calib['roc_auc']:.4f}   "
        f"average precision = {calib['average_precision']:.4f}",
        "",
        f"at the operating threshold ({calib['operating_threshold']:g}):",
        f"  starting    weights: recall={start['at_operating_threshold']['recall']:.4f} "
        f"precision={start['at_operating_threshold']['precision']:.4f} "
        f"FPR={start['at_operating_threshold']['false_positive_rate']:.4f} "
        f"F1={start['at_operating_threshold']['f1']:.4f}",
        f"  calibrated  weights: recall={calib['at_operating_threshold']['recall']:.4f} "
        f"precision={calib['at_operating_threshold']['precision']:.4f} "
        f"FPR={calib['at_operating_threshold']['false_positive_rate']:.4f} "
        f"F1={calib['at_operating_threshold']['f1']:.4f}",
        "",
        f"calibration ({cal['objective']}): environmental "
        f"{cal['starting_weights']['environmental']:g} -> "
        f"{cal['calibrated_weights']['environmental']:g} "
        f"(objective {cal['baseline_value']:.4f} -> {cal['calibrated_value']:.4f})",
        "",
        "per-error-type recall at the operating threshold (calibrated):",
    ]
    for kind, value in calib["per_type_recall_at_threshold"].items():
        lines.append(f"  {kind:<12} {value:.3f}")
    return "\n".join(lines)


def render_figure(report: dict[str, Any], seed: int, path: Path) -> bool:
    """Render the ROC curve and score distribution. Returns False if skipped."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    cases = build_benchmark(seed)
    prepared = prepare_benchmark(cases)
    frame = fuse_prepared(prepared, FusionWeights(**report["calibration"]["calibrated_weights"]))
    scores = suspicion_scores(frame)
    y = labels_are_suspicious(frame)
    threshold = report["calibrated"]["operating_threshold"]

    fig, (ax_roc, ax_dist) = plt.subplots(1, 2, figsize=(11, 4.6))

    fpr, tpr = roc_curve(scores, y)
    ax_roc.plot(fpr, tpr, color="#1f6f54", linewidth=2)
    ax_roc.plot([0, 1], [0, 1], color="#bbbbbb", linestyle="--", linewidth=1)
    op = metrics_at(scores, y, threshold)
    ax_roc.scatter(
        [op.false_positive_rate],
        [op.recall],
        color="#c0392b",
        zorder=5,
        label=f"operating point (thr {threshold:g})",
    )
    ax_roc.set_xlabel("false positive rate")
    ax_roc.set_ylabel("true positive rate (recall)")
    ax_roc.set_title(f"ROC  (AUC = {report['calibrated']['roc_auc']:.3f})")
    ax_roc.set_xlim(-0.02, 1.02)
    ax_roc.set_ylim(-0.02, 1.02)
    ax_roc.legend(loc="lower right", fontsize=8)

    categories = ["plausible", *ERROR_TYPES]
    rng = np.random.default_rng(0)
    for i, category in enumerate(categories):
        if category == "plausible":
            mask = (frame["label"] == "plausible").to_numpy(dtype=bool)
            color = "#3477b3"
        else:
            mask = (frame["error_type"] == category).to_numpy(dtype=bool)
            color = "#c0392b"
        ys = scores[mask]
        xs = i + (rng.random(ys.shape[0]) - 0.5) * 0.6
        ax_dist.scatter(xs, ys, s=10, alpha=0.5, color=color, edgecolors="none")
    ax_dist.axhline(threshold, color="#444444", linestyle="--", linewidth=1)
    ax_dist.text(
        len(categories) - 0.5,
        threshold + 0.02,
        f"threshold {threshold:g}",
        ha="right",
        va="bottom",
        fontsize=8,
        color="#444444",
    )
    ax_dist.set_xticks(range(len(categories)))
    ax_dist.set_xticklabels(categories, rotation=40, ha="right", fontsize=8)
    ax_dist.set_ylabel("suspicion score")
    ax_dist.set_ylim(-0.03, 1.03)
    ax_dist.set_title("suspicion score by category")

    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate and calibrate the detection engine.")
    parser.add_argument("--seed", type=int, default=0, help="Benchmark seed.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_MIN_SCORE,
        help="Operating threshold to report and calibrate against.",
    )
    parser.add_argument("--grid-steps", type=int, default=90, help="Calibration grid resolution.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs"),
        help="Directory for the results JSON and figure (run from the repo root).",
    )
    parser.add_argument("--no-figure", action="store_true", help="Skip rendering the figure.")
    args = parser.parse_args()

    report = build_report(args.seed, args.threshold, args.grid_steps)
    print(_format_report(report))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results_path = args.output_dir / "evaluation_results.json"
    results_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {results_path}")

    if not args.no_figure:
        figure_path = args.output_dir / "evaluation.png"
        if render_figure(report, args.seed, figure_path):
            print(f"wrote {figure_path}")
        else:
            print(
                "matplotlib not installed; skipped the figure "
                "(install the dev dependencies to render it)"
            )


if __name__ == "__main__":
    main()

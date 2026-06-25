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

from ..data.worldclim import BIO_VARIABLES
from ..engine.fusion import FusionWeights
from ..explain.cluster import DEFAULT_MIN_SCORE
from .benchmark import (
    base_cleaning_summary,
    benchmark_label_counts,
    build_benchmark,
    build_real_case,
    clean_base_population,
)
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
    PreparedCase,
    fuse_prepared,
    labels_are_suspicious,
    prepare_benchmark,
    prepare_case,
    suspicion_scores,
)
from .split import split_prepared

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


def build_real_report(
    base: pd.DataFrame,
    *,
    name: str,
    expected_realm: str,
    doi: str | None = None,
    variables: tuple[int, ...] = BIO_VARIABLES,
    threshold: float = DEFAULT_MIN_SCORE,
    grid_steps: int = 90,
    holdout_frac: float = 0.5,
    errors_per_type: int = 50,
    seed: int = 0,
) -> dict[str, Any]:
    """Evaluate the engine on a real, DOI-backed frame with a held-out split.

    The plausible frame is first cleaned of records that fail basic
    coordinate-quality checks (reported separately as findings), then the six error
    types are planted into it, the upstream signals are prepared once, and the
    records are split into a calibration fold and a held-out report fold. Only the
    environmental weight is calibrated, on the calibration fold; the deterministic
    rule confidences are fixed. Every headline metric is reported on the held-out
    fold, which removes the at-threshold optimism of in-sample calibration. Enough
    errors are planted per type (``errors_per_type``) for the per-type recall to be
    a meaningful estimate rather than a count of two or three.
    """
    from ..taxa import Realm

    realm: Realm = expected_realm  # type: ignore[assignment]
    clean_base, dropped = clean_base_population(base, expected_realm=realm)
    case = build_real_case(
        clean_base,
        name=name,
        expected_realm=realm,
        variables=variables,
        errors_per_type=errors_per_type,
        seed=seed,
    )
    prepared = prepare_case(case, variables=variables)
    calib_case, holdout_case = split_prepared(prepared, holdout_frac=holdout_frac, seed=seed)

    calibration = calibrate(
        [calib_case],
        objective=f1_at_threshold_objective(threshold),
        objective_name=f"f1@{threshold:g}",
        start=STARTING_WEIGHTS,
        grid_steps=grid_steps,
    )

    holdout_starting = fuse_prepared([holdout_case], STARTING_WEIGHTS)
    holdout_calibrated = fuse_prepared([holdout_case], calibration.weights)
    calib_calibrated = fuse_prepared([calib_case], calibration.weights)

    def fold_counts(prepared_case: PreparedCase) -> dict[str, int]:
        labels = prepared_case.frame["label"]
        plausible = int((labels == "plausible").sum())
        suspicious = int((labels == "suspicious").sum())
        return {"plausible": plausible, "suspicious": suspicious, "total": plausible + suspicious}

    return {
        "mode": "real",
        "taxon": name,
        "doi": doi,
        "seed": seed,
        "holdout_frac": holdout_frac,
        "errors_per_type": errors_per_type,
        "base_cleaning": {
            **base_cleaning_summary(dropped),
            "plausible_kept": int(len(clean_base)),
        },
        "fold_counts": {
            "calibration": fold_counts(calib_case),
            "holdout": fold_counts(holdout_case),
        },
        "calibration": {
            "objective": calibration.objective_name,
            "baseline_value": calibration.baseline_value,
            "calibrated_value": calibration.objective_value,
            "improvement": calibration.improvement,
            "starting_weights": vars(STARTING_WEIGHTS),
            "calibrated_weights": vars(calibration.weights),
        },
        "calibration_fold": evaluate(calib_calibrated, threshold),
        "holdout_starting": evaluate(holdout_starting, threshold),
        "holdout": evaluate(holdout_calibrated, threshold),
    }


def _format_real_report(report: dict[str, Any]) -> str:
    cal = report["calibration"]
    folds = report["fold_counts"]
    hold = report["holdout"]
    hold_start = report["holdout_starting"]
    calib_fold = report["calibration_fold"]
    clean = report["base_cleaning"]
    lines = [
        "TaxonGuard evaluation (real GBIF data, held-out split)",
        "======================================================",
        f"taxon: {report['taxon']}   DOI: {report['doi'] or 'not recorded'}   "
        f"seed {report['seed']}",
        f"real anomalies removed from the plausible class before planting: "
        f"{clean['total']} "
        f"(open-ocean {clean.get('realm_mismatch', 0)}, "
        f"null-island {clean.get('zero_coordinates', 0)}, "
        f"lat=lon {clean.get('equal_coordinates', 0)}); "
        f"{clean['plausible_kept']} verified-plausible records kept",
        f"calibration fold: {folds['calibration']['total']} records "
        f"({folds['calibration']['plausible']} plausible, "
        f"{folds['calibration']['suspicious']} planted errors)",
        f"held-out fold:    {folds['holdout']['total']} records "
        f"({folds['holdout']['plausible']} plausible, "
        f"{folds['holdout']['suspicious']} planted errors)",
        "",
        "held-out ranking quality (calibrated weights):",
        f"  ROC-AUC = {hold['roc_auc']:.4f}   average precision = {hold['average_precision']:.4f}",
        "",
        f"held-out at the operating threshold ({hold['operating_threshold']:g}):",
        f"  starting    weights: recall={hold_start['at_operating_threshold']['recall']:.4f} "
        f"precision={hold_start['at_operating_threshold']['precision']:.4f} "
        f"FPR={hold_start['at_operating_threshold']['false_positive_rate']:.4f} "
        f"F1={hold_start['at_operating_threshold']['f1']:.4f}",
        f"  calibrated  weights: recall={hold['at_operating_threshold']['recall']:.4f} "
        f"precision={hold['at_operating_threshold']['precision']:.4f} "
        f"FPR={hold['at_operating_threshold']['false_positive_rate']:.4f} "
        f"F1={hold['at_operating_threshold']['f1']:.4f}",
        "",
        f"calibration-fold F1 (in-sample, for reference): "
        f"{calib_fold['at_operating_threshold']['f1']:.4f}",
        "",
        f"calibration ({cal['objective']}): environmental "
        f"{cal['starting_weights']['environmental']:g} -> "
        f"{cal['calibrated_weights']['environmental']:g}",
        "",
        "held-out per-error-type recall  (principled weights -> calibrated):",
    ]
    starting_recall = hold_start["per_type_recall_at_threshold"]
    for kind, value in hold["per_type_recall_at_threshold"].items():
        start_value = starting_recall.get(kind, float("nan"))
        lines.append(f"  {kind:<12} {start_value:.3f} -> {value:.3f}")
    return "\n".join(lines)


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


def _render_panels(
    frame: pd.DataFrame,
    scores: np.ndarray,
    y: np.ndarray,
    threshold: float,
    roc_auc_value: float,
    path: Path,
    *,
    title_suffix: str = "",
) -> bool:
    """Render the ROC curve and score-by-category panels for an already-fused frame.

    Returns False if matplotlib is not installed, so the core evaluation never
    depends on a plotting library.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False

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
    ax_roc.set_title(f"ROC{title_suffix}  (AUC = {roc_auc_value:.3f})")
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
    ax_dist.set_title(f"suspicion score by category{title_suffix}")

    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return True


def render_figure(report: dict[str, Any], seed: int, path: Path) -> bool:
    """Render the synthetic-benchmark figure. Returns False if skipped."""
    cases = build_benchmark(seed)
    prepared = prepare_benchmark(cases)
    frame = fuse_prepared(prepared, FusionWeights(**report["calibration"]["calibrated_weights"]))
    scores = suspicion_scores(frame)
    y = labels_are_suspicious(frame)
    threshold = report["calibrated"]["operating_threshold"]
    return _render_panels(frame, scores, y, threshold, report["calibrated"]["roc_auc"], path)


def render_real_figure(
    report: dict[str, Any],
    base: pd.DataFrame,
    *,
    name: str,
    expected_realm: str,
    variables: tuple[int, ...],
    path: Path,
) -> bool:
    """Render the held-out real-data figure. Returns False if skipped."""
    from ..taxa import Realm

    realm: Realm = expected_realm  # type: ignore[assignment]
    clean_base, _ = clean_base_population(base, expected_realm=realm)
    case = build_real_case(
        clean_base,
        name=name,
        expected_realm=realm,
        variables=variables,
        errors_per_type=int(report.get("errors_per_type", 50)),
        seed=report["seed"],
    )
    prepared = prepare_case(case, variables=variables)
    _, holdout_case = split_prepared(
        prepared, holdout_frac=report["holdout_frac"], seed=report["seed"]
    )
    frame = fuse_prepared(
        [holdout_case], FusionWeights(**report["calibration"]["calibrated_weights"])
    )
    scores = suspicion_scores(frame)
    y = labels_are_suspicious(frame)
    threshold = report["holdout"]["operating_threshold"]
    return _render_panels(
        frame, scores, y, threshold, report["holdout"]["roc_auc"], path, title_suffix=" (held-out)"
    )


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
    parser.add_argument(
        "--real-cache",
        type=Path,
        default=None,
        help="Path to an enriched real-data parquet (from data.download --build). "
        "Switches to the held-out real-data evaluation.",
    )
    parser.add_argument(
        "--taxon", default="Rana temporaria", help="Taxon name for the real-data report."
    )
    parser.add_argument(
        "--realm", default="freshwater", help="Expected realm for the real-data taxon."
    )
    parser.add_argument("--doi", default=None, help="DOI to record in the real-data report.")
    parser.add_argument(
        "--holdout-frac", type=float, default=0.5, help="Held-out fraction for the real-data split."
    )
    args = parser.parse_args()

    if args.real_cache is not None:
        _run_real(args)
        return

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


def _run_real(args: argparse.Namespace) -> None:
    """Run the held-out real-data evaluation from a cached enriched parquet."""
    base = pd.read_parquet(args.real_cache)
    doi = args.doi
    sidecar = args.real_cache.with_suffix(".json")
    if doi is None and sidecar.exists():
        doi = json.loads(sidecar.read_text()).get("doi")

    report = build_real_report(
        base,
        name=args.taxon,
        expected_realm=args.realm,
        doi=doi,
        threshold=args.threshold,
        grid_steps=args.grid_steps,
        holdout_frac=args.holdout_frac,
        seed=args.seed,
    )
    print(_format_real_report(report))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    results_path = args.output_dir / "evaluation_real_results.json"
    results_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {results_path}")

    if not args.no_figure:
        figure_path = args.output_dir / "evaluation_real.png"
        if render_real_figure(
            report,
            base,
            name=args.taxon,
            expected_realm=args.realm,
            variables=BIO_VARIABLES,
            path=figure_path,
        ):
            print(f"wrote {figure_path}")
        else:
            print("matplotlib not installed; skipped the figure")


if __name__ == "__main__":
    main()

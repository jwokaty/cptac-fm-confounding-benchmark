"""
evaluate_pb.py

Compiles results from Patho-Bench linear probe and retrieval experiments
for all models, datasets, and tasks. Reports mean ± SE for each metric.

Requires pb_linprobe.py and pb_retrieval.py to have been run first.

Usage:
    uv run python src/analysis/evaluate_pb.py --experiment linprobe
    uv run python src/analysis/evaluate_pb.py --experiment retrieval
    uv run python src/analysis/evaluate_pb.py --experiment all
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.config import LOGS_DIR, MODELS, RESULTS_DIR, TASKS
from analysis.utils import get_logger

logger = get_logger("evaluate_pb", LOGS_DIR)

METRICS = {
    "linprobe":  ["macro-ovr-auc", "bacc", "macro-f1", "weighted_kappa"],
    "retrieval": ["mAP@5", "mAP@10"],
}


# ── I/O helpers ───────────────────────────────────────────────────────────────

def get_experiment_dir(experiment: str, model: str, dataset: str, task: str) -> Path:
    """Return the results directory for an experiment/model/dataset/task."""
    if experiment == "linprobe":
        return RESULTS_DIR / "linprobe" / model / dataset / task / f"{model}_linprobe"
    return RESULTS_DIR / "retrieval" / model / dataset / task


def get_best_cost_dir(model: str, dataset: str, task: str) -> Path:
    """
    Return the linprobe cost directory with the highest macro-ovr-auc mean.

    Raises:
        ValueError: if no completed cost directories are found.
    """
    sweep_dir = get_experiment_dir("linprobe", model, dataset, task)
    cost_dirs = [
        d for d in sweep_dir.iterdir()
        if d.is_dir() and (d / "test_metrics_summary.json").exists()
    ] if sweep_dir.exists() else []

    if not cost_dirs:
        raise ValueError(
            f"no completed results for {model}/{dataset}/{task} — run pb_linprobe.py first"
        )

    best_dir, best_auc = None, -1
    for d in cost_dirs:
        with open(d / "test_metrics_summary.json") as f:
            results = json.load(f)
        auc = results["macro-ovr-auc"]["mean"]
        if auc > best_auc:
            best_auc = auc
            best_dir = d

    return best_dir


def load_summary_metrics(experiment: str, model: str, dataset: str, task: str) -> dict:
    """
    Load summary metrics from test_metrics_summary.json.

    For linprobe, loads from the best cost directory.
    For retrieval, loads from the task directory directly.

    Returns:
        Dict with mean, se, formatted for each metric.
    """
    metrics = METRICS[experiment]

    if experiment == "linprobe":
        summary_path = get_best_cost_dir(model, dataset, task) / "test_metrics_summary.json"
    else:
        summary_path = get_experiment_dir("retrieval", model, dataset, task) / "test_metrics_summary.json"

    if not summary_path.exists():
        raise FileNotFoundError(f"summary not found at {summary_path}")

    with open(summary_path) as f:
        summary = json.load(f)

    return {m: summary[m] for m in metrics}


# ── results assembly ──────────────────────────────────────────────────────────

def compile_results(experiment: str) -> pd.DataFrame:
    """
    Compile results for all models, datasets and tasks.

    Returns:
        DataFrame with one row per model/dataset/task/metric.
    """
    metrics = METRICS[experiment]
    rows = []

    for model in MODELS:
        for dataset, tasks in TASKS.items():
            for task in tasks:
                try:
                    summary = load_summary_metrics(experiment, model, dataset, task)
                except (FileNotFoundError, ValueError) as e:
                    logger.warning(f"  skipping {model}/{dataset}/{task}: {e}")
                    continue

                for metric in metrics:
                    rows.append({
                        "model":     model,
                        "dataset":   dataset,
                        "task":      task,
                        "metric":    metric,
                        "mean":      summary[metric]["mean"],
                        "se":        summary[metric]["se"],
                        "formatted": summary[metric]["formatted"],
                    })

    return pd.DataFrame(rows)


def save_results(df: pd.DataFrame, experiment: str) -> Path:
    """Save results DataFrame to CSV."""
    output_path = RESULTS_DIR / f"{experiment}_summary.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"results saved to {output_path}")
    return output_path


# ── main ──────────────────────────────────────────────────────────────────────

def run_experiment(experiment: str) -> None:
    """Compile and save results for one experiment type."""
    logger.info(f"compiling {experiment} results...")
    df = compile_results(experiment)

    if df.empty:
        logger.error(f"no {experiment} results found")
        return

    save_results(df, experiment)

    for metric in METRICS[experiment]:
        print(f"\n=== {experiment} / {metric} ===")
        sub = df[df["metric"] == metric][[
            "model", "dataset", "task", "mean", "se", "formatted",
        ]]
        print(sub.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile Patho-Bench results")
    parser.add_argument(
        "--experiment",
        choices=["linprobe", "retrieval", "all"],
        default="all",
        help="which experiment to compile (default: all)",
    )
    args = parser.parse_args()

    if args.experiment in ("linprobe", "all"):
        run_experiment("linprobe")

    if args.experiment in ("retrieval", "all"):
        run_experiment("retrieval")

    logger.info("done")


if __name__ == "__main__":
    main()

"""
evaluate_pb_retrieval.py

Compiles results from Patho-Bench retrieval experiments, runs paired
permutation tests to compare TITAN and mSTAR, applies Benjamini-Hochberg
FDR correction, and saves a summary CSV.

Requires pb_retrieval.py to have been run first.

Usage:
    uv run python src/analysis/evaluate_pb_retrieval.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import permutation_test
from statsmodels.stats.multitest import multipletests

from analysis.config import LOGS_DIR, MODELS, RESULTS_DIR, TASKS
from analysis.utils import get_logger

logger = get_logger("evaluate_pb_retrieval", LOGS_DIR)

FDR_ALPHA = 0.10
METRICS   = ["mAP@5", "mAP@10"]


# ── I/O helpers ───────────────────────────────────────────────────────────────

def get_retrieval_dir(model: str, dataset: str, task: str) -> Path:
    """Return the retrieval results directory for a model/dataset/task."""
    return RESULTS_DIR / "retrieval" / model / dataset / task


def load_fold_metrics(model: str, dataset: str, task: str) -> dict[str, np.ndarray]:
    """
    Load per-fold metric values from retrieval results.

    Returns:
        Dict mapping metric name to array of shape (n_folds,).
    """
    fold_dir = get_retrieval_dir(model, dataset, task) / "test_metrics"

    if not fold_dir.exists():
        raise FileNotFoundError(
            f"retrieval results not found at {fold_dir} — run pb_retrieval.py first"
        )

    fold_values: dict[str, list] = {m: [] for m in METRICS}

    for fold_path in sorted(fold_dir.iterdir()):
        metrics_path = fold_path / "metrics.json"
        if not metrics_path.exists():
            continue
        with open(metrics_path) as f:
            data = json.load(f)
        for metric in METRICS:
            fold_values[metric].append(data["overall"][metric])

    return {m: np.array(v) for m, v in fold_values.items()}


def load_summary_metrics(model: str, dataset: str, task: str) -> dict:
    """
    Load summary metrics from test_metrics_summary.json.

    Returns:
        Dict with mean and se for each metric in METRICS.
    """
    summary_path = get_retrieval_dir(model, dataset, task) / "test_metrics_summary.json"
    with open(summary_path) as f:
        summary = json.load(f)
    return {m: summary[m] for m in METRICS}


# ── permutation test ──────────────────────────────────────────────────────────

def run_permutation_test(
    titan_values: np.ndarray,
    mstar_values: np.ndarray,
) -> float:
    """
    Run a paired permutation test comparing TITAN and mSTAR across folds.

    Tests the null hypothesis that the two models perform equivalently.
    The test statistic is the mean difference (TITAN - mSTAR) across folds.

    Args:
        titan_values: array of shape (n_folds,) with per-fold metric values
        mstar_values: array of shape (n_folds,) with per-fold metric values

    Returns:
        Two-sided p-value.
    """
    def statistic(x, y, axis):
        return np.mean(x - y, axis=axis)

    result = permutation_test(
        (titan_values, mstar_values),
        statistic,
        permutation_type = "samples",
        n_resamples      = 10_000,
        alternative      = "two-sided",
    )
    return result.pvalue


# ── results assembly ──────────────────────────────────────────────────────────

def compile_results() -> pd.DataFrame:
    """
    Compile retrieval results for all models, datasets and tasks.

    Loads per-fold metric values, runs permutation tests comparing TITAN and
    mSTAR, applies BH FDR correction, and assembles a summary table.

    Returns:
        DataFrame with one row per model/dataset/task/metric combination.
    """
    rows       = []
    ptest_rows = []  # one per dataset/task/metric for FDR correction

    for dataset, tasks in TASKS.items():
        for task in tasks:
            try:
                titan_folds = load_fold_metrics("titan", dataset, task)
                mstar_folds = load_fold_metrics("mstar", dataset, task)
            except FileNotFoundError as e:
                logger.warning(f"  skipping {dataset}/{task}: {e}")
                continue

            titan_summary = load_summary_metrics("titan", dataset, task)
            mstar_summary = load_summary_metrics("mstar", dataset, task)

            for metric in METRICS:
                p = run_permutation_test(titan_folds[metric], mstar_folds[metric])

                ptest_rows.append({
                    "dataset": dataset,
                    "task":    task,
                    "metric":  metric,
                    "p_value": p,
                })

                for model, summary, folds in [
                    ("titan", titan_summary, titan_folds),
                    ("mstar", mstar_summary, mstar_folds),
                ]:
                    rows.append({
                        "model":        model,
                        "dataset":      dataset,
                        "task":         task,
                        "metric":       metric,
                        "mean":         summary[metric]["mean"],
                        "se":           summary[metric]["se"],
                        "formatted":    summary[metric]["formatted"],
                        "p_vs_other":   p,
                    })

    df      = pd.DataFrame(rows)
    ptest_df = pd.DataFrame(ptest_rows)

    if ptest_df.empty:
        logger.error("no results found — check that pb_retrieval.py has been run")
        return df

    # BH FDR correction across all dataset/task/metric combinations
    reject, pvals_corrected, _, _ = multipletests(
        ptest_df["p_value"].values,
        alpha  = FDR_ALPHA,
        method = "fdr_bh",
    )
    ptest_df["p_value_fdr"]  = pvals_corrected
    ptest_df["significant"]  = reject

    # merge FDR-corrected p-values back into main df
    df = df.merge(
        ptest_df[["dataset", "task", "metric", "p_value_fdr", "significant"]],
        on  = ["dataset", "task", "metric"],
        how = "left",
    )

    return df


def save_results(df: pd.DataFrame) -> Path:
    """Save results DataFrame to CSV."""
    output_path = RESULTS_DIR / "retrieval_summary.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"results saved to {output_path}")
    return output_path


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("compiling retrieval results...")
    df = compile_results()

    if df.empty:
        logger.error("no results to report")
        return

    save_results(df)

    # print summary table — one row per model/dataset/task for each metric
    for metric in METRICS:
        print(f"\n=== {metric} ===")
        sub = df[df["metric"] == metric][[
            "model", "dataset", "task",
            "mean", "se", "formatted",
            "p_vs_other", "p_value_fdr", "significant",
        ]]
        print(sub.to_string(index=False))

    logger.info("done")


if __name__ == "__main__":
    main()

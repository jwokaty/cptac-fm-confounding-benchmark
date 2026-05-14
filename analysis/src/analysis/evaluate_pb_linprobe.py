"""
evaluate_pb_linprobe.py

Compiles results from Patho-Bench linear probe experiments, runs paired
permutation tests to compare TITAN and mSTAR, applies Benjamini-Hochberg
FDR correction, saves a summary CSV, and generates visualizations.

Requires pb_linprobe.py to have been run first.

Usage:
    uv run python src/analysis/evaluate_pb_linprobe.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import permutation_test
from statsmodels.stats.multitest import multipletests

from analysis.config import LOGS_DIR, MODELS, RESULTS_DIR, TASKS
from analysis.utils import get_logger
from analysis.pb_linprobe import get_cost_dirs, read_best_results

logger = get_logger("evaluate_pb_linprobe", LOGS_DIR)

FDR_ALPHA = 0.10
METRICS = ["macro-ovr-auc", "bacc", "macro-f1", "weighted_kappa"]


def get_best_cost_dir(model: str, dataset: str, task: str) -> Path:
    """
    Return the cost directory with the highest macro-ovr-auc mean.

    Args:
        model:   model name
        dataset: dataset name
        task:    task name

    Returns:
        Path to the best cost directory.

    Raises:
        ValueError: if no completed cost directories are found.
    """
    cost_dirs = get_cost_dirs(model, dataset, task)
    if not cost_dirs:
        raise ValueError(
            f"no completed results for {model}/{dataset}/{task} — run pb_linprobe.py first"
        )
    _, best_cost = read_best_results(model, dataset, task)
    sweep_dir = RESULTS_DIR / "linprobe" / model / dataset / task / f"{model}_linprobe"
    return sweep_dir / best_cost


def load_fold_aucs(model: str, dataset: str, task: str) -> np.ndarray:
    """
    Load per-fold macro-ovr-auc values from the best cost directory.

    Args:
        model:   model name
        dataset: dataset name
        task:    task name

    Returns:
        Array of shape (50,) with per-fold AUC values.
    """
    best_dir = get_best_cost_dir(model, dataset, task)
    fold_dir = best_dir / "test_metrics"
    aucs = []
    for fold in sorted(fold_dir.iterdir()):
        with open(fold / "metrics.json") as f:
            metrics = json.load(f)
        aucs.append(metrics["overall"]["macro-ovr-auc"])
    return np.array(aucs)


def load_summary_metrics(model: str, dataset: str, task: str) -> dict:
    """
    Load summary metrics from the best cost directory.

    Args:
        model:   model name
        dataset: dataset name
        task:    task name

    Returns:
        Dictionary with mean and se for each metric in METRICS.
    """
    best_dir = get_best_cost_dir(model, dataset, task)
    with open(best_dir / "test_metrics_summary.json") as f:
        summary = json.load(f)
    return {m: summary[m] for m in METRICS}


def run_permutation_test(
    titan_aucs: np.ndarray,
    mstar_aucs: np.ndarray,
) -> float:
    """
    Run a paired permutation test comparing TITAN and mSTAR AUCs across folds.

    Tests the null hypothesis that the two models perform equivalently.
    The test statistic is the mean difference (TITAN - mSTAR) across folds.

    Args:
        titan_aucs: array of shape (50,) with per-fold AUC values for TITAN
        mstar_aucs: array of shape (50,) with per-fold AUC values for mSTAR

    Returns:
        Two-sided p-value.
    """
    def statistic(x, y, axis):
        return np.mean(x - y, axis=axis)

    result = permutation_test(
        (titan_aucs, mstar_aucs),
        statistic,
        permutation_type = "samples",
        n_resamples = 10000,
        alternative = "two-sided",
    )
    return result.pvalue


def run_vs_chance_test(aucs: np.ndarray) -> float:
    """
    Run a one-sample permutation test against chance (AUC = 0.5).

    Tests the null hypothesis that the model performs no better than chance.

    Args:
        aucs: array of shape (50,) with per-fold AUC values

    Returns:
        One-sided p-value (greater than chance).
    """
    def statistic(x, axis):
        return np.mean(x - 0.5, axis=axis)

    result = permutation_test(
        (aucs,),
        statistic,
        permutation_type = "samples",
        n_resamples = 10000,
        alternative = "greater",
    )
    return result.pvalue


def compile_results() -> pd.DataFrame:
    """
    Compile results for all models, datasets and tasks into a DataFrame.

    Loads per-fold AUC values, runs permutation tests, applies BH FDR
    correction, and assembles a summary table.

    Returns:
        DataFrame with one row per model/dataset/task combination.
    """
    rows = []

    for dataset, tasks in TASKS.items():
        for task in tasks:
            titan_aucs = load_fold_aucs("titan", dataset, task)
            mstar_aucs = load_fold_aucs("mstar", dataset, task)

            p_titan_vs_mstar = run_permutation_test(titan_aucs, mstar_aucs)
            p_titan_vs_chance = run_vs_chance_test(titan_aucs)
            p_mstar_vs_chance = run_vs_chance_test(mstar_aucs)

            for model in MODELS:
                summary = load_summary_metrics(model, dataset, task)

                row = {
                    "model": model,
                    "dataset": dataset,
                    "task": task,
                    "p_vs_chance": p_titan_vs_chance if model == "titan" else p_mstar_vs_chance,
                    "p_vs_other": p_titan_vs_mstar,
                }

                for metric in METRICS:
                    row[f"{metric}_mean"] = summary[metric]["mean"]
                    row[f"{metric}_se"] = summary[metric]["se"]

                rows.append(row)

    df = pd.DataFrame(rows)

    # apply BH FDR correction to TITAN vs mSTAR p-values (one per task)
    task_rows = df[df["model"] == "titan"].copy()
    reject, pvals_corrected, _, _ = multipletests(
        task_rows["p_vs_other"].values,
        alpha = FDR_ALPHA,
        method = "fdr_bh",
    )
    task_rows["p_vs_other_fdr"] = pvals_corrected
    task_rows["significant"] = reject

    # apply BH FDR correction to vs-chance p-values across all model/task combinations
    reject_chance, pvals_chance_corrected, _, _ = multipletests(
        df["p_vs_chance"].values,
        alpha = FDR_ALPHA,
        method = "fdr_bh",
    )
    df["p_vs_chance_fdr"] = pvals_chance_corrected
    df["significant_vs_chance"] = reject_chance

    # merge FDR-corrected between-model p-values back into main df
    fdr_cols = task_rows[["dataset", "task", "p_vs_other_fdr", "significant"]]
    df = df.merge(fdr_cols, on = ["dataset", "task"], how = "left")

    return df


def save_results(df: pd.DataFrame) -> Path:
    """
    Save results DataFrame to CSV.

    Args:
        df: results DataFrame from compile_results()

    Returns:
        Path to saved CSV file.
    """
    output_path = RESULTS_DIR / "linprobe_summary.csv"
    output_path.parent.mkdir(parents = True, exist_ok = True)
    df.to_csv(output_path, index = False)
    logger.info(f"results saved to {output_path}")
    return output_path


def main() -> None:
    logger.info("compiling results...")
    df = compile_results()
    save_results(df)
    logger.info("done")
    print(df[[
        "model", "dataset", "task",
        "macro-ovr-auc_mean", "macro-ovr-auc_se",
        "p_vs_other", "p_vs_other_fdr", "significant"
    ]].to_string())


if __name__ == "__main__":
    main()

"""
confounding_analysis.py

Dawood-style stratified confounding analysis for TITAN and mSTAR.

For each task, loads per-patient predicted scores from generate_predictions.py,
joins clinical covariates, and runs a stratified permutation test (following
Dawood et al., Nature Biomedical Engineering 2026) to assess whether model
performance is stable across clinically meaningful subgroups.

Experiment design:
    PTEN_mutation (UCEC) — stratified by MSI status (MSS / MSI-H)
    ER_status     (BRCA) — stratified by PAM50 subtype (Basal/LumA/LumB/Her2/Normal-like)

For each stratum the test asks: is the observed AUROC within this subgroup
significantly different from what would be expected if the stratifying variable
were randomly assigned? A significantly low AUROC in a stratum is consistent
with the model relying on that stratifying variable as a confounder rather than
reading genuine molecular signal.

Output:
    analysis/results/confounding/{model}/{dataset}/{task}/results.csv
        stratum, n_patients, n_positive, auroc, p_value, p_value_fdr, significant

    analysis/results/confounding/summary.csv
        model, dataset, task, stratum, ...

Usage:
    uv run python src/analysis/confounding_analysis.py
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from statsmodels.stats.multitest import multipletests

from analysis.config import (CLINICAL_FILES, CONFOUNDING_DIR, FDR_ALPHA,
                             LOGS_DIR, MODELS, PERM_RUNS, PREDICTIONS_DIR,
                             RANDOM_STATE, RESULTS_DIR, STRATIFIED_TASKS)
from analysis.utils import get_logger

logger = get_logger("confounding_analysis", LOGS_DIR)


def load_scores(model: str, dataset: str, task: str) -> pd.DataFrame:
    """
    Load per-patient predicted scores from generate_predictions.py output.

    Returns DataFrame with columns [case_id, true_label, score].
    """
    path = PREDICTIONS_DIR / model / dataset / task / "scores.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"scores not found at {path} — run generate_predictions.py first"
        )
    return pd.read_csv(path)


def load_clinical(dataset: str, stratifier_col: str) -> pd.DataFrame:
    """
    Load clinical data and return a DataFrame with case_id and stratifier column.
    Drops rows with missing stratifier values.
    """
    path = CLINICAL_FILES[dataset]
    df = pd.read_csv(path, sep = "\t")
    df = df.rename(columns = {"Patient ID": "case_id"})
    if dataset == "cptac_brca":
        df["case_id"] = df["case_id"].str.lstrip("X")
    df = df[["case_id", stratifier_col]].dropna(subset = [stratifier_col])
    df = df[~df[stratifier_col].str.strip().isin(("", "NA", "[Not Available]"))]
    return df


def merge_scores_clinical(
    scores_df: pd.DataFrame,
    clinical_df: pd.DataFrame,
    stratifier_col: str,
) -> pd.DataFrame:
    """
    Merge predicted scores with clinical stratifier.
    Drops patients with missing stratifier values.
    """
    df = scores_df.merge(clinical_df, on = "case_id", how = "inner")
    df = df.dropna(subset = [stratifier_col])
    return df.reset_index(drop = True)


def stratified_permutation_test(
    labels: np.ndarray,
    scores: np.ndarray,
    voi: np.ndarray,
) -> tuple[list[str], list[float], list[float]]:
    """
    Dawood-style stratified permutation test.

    For each unique value of the variable of interest (voi), computes the
    observed AUROC within that stratum, then builds a null distribution by
    randomly permuting voi assignments PERM_RUNS times and recomputing AUROC
    within the shuffled stratum of the same size. The two-sided p-value is the
    proportion of permuted AUROCs as or more extreme than the observed value.

    Args:
        labels: (n,) array of true binary labels
        scores: (n,) array of predicted probabilities
        voi:    (n,) array of stratifying variable values (e.g. MSI status)

    Returns:
        strata:       list of unique stratum names
        observed_aucs: observed AUROC for each stratum
        p_values:     two-sided permutation p-value for each stratum
    """
    rng    = np.random.default_rng(RANDOM_STATE)
    uvals  = sorted(set(voi))
    n      = len(voi)

    # build null distribution — shape (PERM_RUNS, n_strata)
    B = np.full((PERM_RUNS, len(uvals)), np.nan)
    for i in range(PERM_RUNS):
        perm_voi = rng.permutation(voi)
        for j, v in enumerate(uvals):
            mask = perm_voi == v
            if mask.sum() < 2 or len(np.unique(labels[mask])) < 2:
                continue
            try:
                B[i, j] = roc_auc_score(labels[mask], scores[mask])
            except Exception:
                continue

    # observed AUROCs and p-values
    observed_aucs = []
    p_values      = []

    for j, v in enumerate(uvals):
        mask = voi == v
        if mask.sum() < 2 or len(np.unique(labels[mask])) < 2:
            logger.warning(f"    stratum '{v}': insufficient data for AUROC, skipping")
            observed_aucs.append(np.nan)
            p_values.append(np.nan)
            continue

        try:
            f = roc_auc_score(labels[mask], scores[mask])
        except Exception:
            observed_aucs.append(np.nan)
            p_values.append(np.nan)
            continue

        null = B[:, j]
        null = null[~np.isnan(null)]

        if len(null) == 0:
            p_val = np.nan
        else:
            p_val = 2 * min(np.mean(f >= null), np.mean(f <= null))
            # floor at 1/PERM_RUNS
            p_val = max(p_val, 1.0 / PERM_RUNS)

        observed_aucs.append(f)
        p_values.append(p_val)

        logger.info(
            f"    stratum '{v}': n = {mask.sum()}  "
            f"pos = {labels[mask].sum()}  "
            f"AUROC = {f:.3f}  p = {p_val:.4f}"
        )

    return uvals, observed_aucs, p_values

def run_task(
    model: str,
    dataset: str,
    task: str,
    stratifier_col: str,
    stratifier_name: str,
) -> pd.DataFrame:
    """
    Run the full confounding analysis for one model/dataset/task.

    Returns a DataFrame with one row per stratum.
    """
    logger.info(f"  loading scores...")
    scores_df   = load_scores(model, dataset, task)
    clinical_df = load_clinical(dataset, stratifier_col)
    df          = merge_scores_clinical(scores_df, clinical_df, stratifier_col)

    logger.info(
        f"  {len(df)} patients after joining clinical data  "
        f"(pos = {df['true_label'].sum()}, neg = {(df['true_label'] == 0).sum()})"
    )

    # overall AUROC
    try:
        overall_auc = roc_auc_score(df["true_label"].values, df["score"].values)
    except Exception:
        overall_auc = np.nan
    logger.info(f"  overall AUROC: {overall_auc:.3f}")

    # stratified permutation test
    logger.info(f"  running permutation test ({PERM_RUNS:,} permutations)...")
    strata, observed_aucs, p_values = stratified_permutation_test(
        labels = df["true_label"].values,
        scores = df["score"].values,
        voi    = df[stratifier_col].values,
    )

    # BH FDR correction across strata
    valid_mask = [not np.isnan(p) for p in p_values]
    p_fdr      = np.full(len(p_values), np.nan)

    if sum(valid_mask) > 0:
        valid_p = [p_values[i] for i in range(len(p_values)) if valid_mask[i]]
        _, corrected, _, _ = multipletests(valid_p, alpha=FDR_ALPHA, method="fdr_bh")
        idx = 0
        for i in range(len(p_values)):
            if valid_mask[i]:
                p_fdr[i] = corrected[idx]
                idx += 1

    # assemble results
    rows = []
    for j, v in enumerate(strata):
        mask = df[stratifier_col].values == v
        rows.append({
            "model":           model,
            "dataset":         dataset,
            "task":            task,
            "stratifier":      stratifier_name,
            "stratum":         v,
            "n_patients":      int(mask.sum()),
            "n_positive":      int(df.loc[mask, "true_label"].sum()),
            "overall_auroc":   round(overall_auc, 4),
            "stratum_auroc":   round(observed_aucs[j], 4) if not np.isnan(observed_aucs[j]) else np.nan,
            "p_value":         round(p_values[j], 6)      if not np.isnan(p_values[j])      else np.nan,
            "p_value_fdr":     round(float(p_fdr[j]), 6)  if not np.isnan(p_fdr[j])         else np.nan,
            "significant":     bool(p_fdr[j] < FDR_ALPHA) if not np.isnan(p_fdr[j])         else False,
        })

    return pd.DataFrame(rows)


def save_results(df: pd.DataFrame, model: str, dataset: str, task: str) -> None:
    """Save per-task results CSV."""
    out_dir = CONFOUNDING_DIR / model / dataset / task
    out_dir.mkdir(parents = True, exist_ok = True)
    path = out_dir / "results.csv"
    df.to_csv(path, index=False)
    logger.info(f"  → {path}")


def main() -> None:
    all_results = []

    for model in MODELS:
        for dataset, tasks in STRATIFIED_TASKS.items():
            for task, stratifier_col, stratifier_name in tasks:
                logger.info(f"=== {model} / {dataset} / {task} ===")

                try:
                    results_df = run_task(
                        model, dataset, task,
                        stratifier_col, stratifier_name,
                    )
                    save_results(results_df, model, dataset, task)
                    all_results.append(results_df)
                except FileNotFoundError as e:
                    logger.error(f"  {e}")
                except Exception as e:
                    logger.error(f"  failed: {e}")
                    raise

    if all_results:
        summary = pd.concat(all_results, ignore_index=True)
        summary_path = CONFOUNDING_DIR / "summary.csv"
        summary_path.parent.mkdir(parents = True, exist_ok=True)
        summary.to_csv(summary_path, index = False)
        logger.info(f"\nsummary saved to {summary_path}")
        print("\n" + summary.to_string(index = False))

    logger.info("=== complete ===")


if __name__ == "__main__":
    main()

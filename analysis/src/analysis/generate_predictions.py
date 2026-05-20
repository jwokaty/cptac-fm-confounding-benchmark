"""
generate_predictions.py

Generates per-patient predicted scores for the confounding analysis by running
stratified k-fold cross-validation (logistic regression) on case-level
embeddings. Produces one predicted score per patient per model per task.

Output:
    analysis/predictions/{model}/{dataset}/{task}/scores.csv
        case_id, true_label, score

    analysis/predictions/{model}/{dataset}/{task}/metrics.csv
        fold, macro-ovr-auc, bacc, weighted_kappa, macro-f1

Tasks are defined in CONFOUNDING_TASKS below. Labels are loaded from the
cBioPortal clinical data files specified in CLINICAL_FILES.

Usage:
    uv run python src/analysis/generate_predictions.py
"""

from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    balanced_accuracy_score,
    cohen_kappa_score,
    f1_score,
    roc_auc_score,
)

from analysis.config import (CLINICAL_FILES, CONFOUNDING_TASKS, EMBEDDINGS,
                             LOGS_DIR, MODELS, N_FOLDS, PREDICTIONS_DIR,
                             RANDOM_STATE, RESULTS_DIR)
from analysis.utils import get_logger

logger = get_logger("generate_predictions", LOGS_DIR)


def load_embedding(h5_path: Path) -> np.ndarray:
    """Load a case-level embedding from an .h5 file → 1-D float32 array."""
    with h5py.File(h5_path, "r") as f:
        return f["features"][:].squeeze().astype(np.float32)


def load_clinical(dataset: str) -> pd.DataFrame:
    """Load clinical data for a dataset, indexed by Patient ID."""
    path = CLINICAL_FILES[dataset]
    df = pd.read_csv(path, sep = "\t")
    if "Patient ID" in df.columns:
        df = df.rename(columns = {"Patient ID": "case_id"})
    if dataset == "cptac_brca":
        df["case_id"] = df["case_id"].str.lstrip("X")
    return df.set_index("case_id")


def load_dataset(
    model: str,
    dataset: str,
    label_col: str,
    label_map: dict | None,
    clinical_df: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Load embeddings and labels for all patients with valid data.

    Returns:
        X:        (n_patients, embed_dim) array of embeddings
        y:        (n_patients,) array of integer labels
        case_ids: (n_patients,) array of case ID strings
    """
    embeddings_dir = EMBEDDINGS[model][dataset]

    X, y, case_ids = [], [], []
    missing_label = []

    for h5_path in sorted(embeddings_dir.glob("*.h5")):
        case_id = h5_path.stem

        if case_id not in clinical_df.index:
            missing_label.append(case_id)
            continue

        raw_label = clinical_df.loc[case_id, label_col]

        # skip missing or ambiguous labels
        if pd.isna(raw_label) or str(raw_label).strip() in ("", "NA", "[Not Available]"):
            continue

        if label_map is not None:
            if raw_label not in label_map:
                continue
            label = label_map[raw_label]
        else:
            label = int(raw_label)

        X.append(load_embedding(h5_path))
        y.append(label)
        case_ids.append(case_id)

    if missing_label:
        logger.warning(f"  {len(missing_label)} cases not found in clinical data")

    logger.info(
        f"  loaded {len(case_ids)} patients  "
        f"(positive = {sum(y)}, negative = {len(y) - sum(y)})"
    )

    return np.array(X), np.array(y), np.array(case_ids)


def run_cv(
    X: np.ndarray,
    y: np.ndarray,
    case_ids: np.ndarray,
    cost: float = 1.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run stratified k-fold cross-validation and collect per-patient scores.

    Each patient appears in the test set exactly once. The logistic regression
    model is discarded after each fold — only the predicted scores are saved.

    Args:
        X:        (n_patients, embed_dim) embedding matrix
        y:        (n_patients,) label array
        case_ids: (n_patients,) case ID array
        cost:     logistic regression regularisation strength (C parameter)

    Returns:
        scores_df:  DataFrame with columns [case_id, true_label, score]
        metrics_df: DataFrame with per-fold metrics
    """
    skf = StratifiedKFold(n_splits = N_FOLDS, shuffle = True,
                          random_state = RANDOM_STATE)

    score_rows  = []
    metric_rows = []

    for fold, (train_idx, test_idx) in enumerate(skf.split(X, y)):
        X_train, y_train = X[train_idx], y[train_idx]
        X_test,  y_test  = X[test_idx],  y[test_idx]

        clf = LogisticRegression(C = cost, max_iter = 1000,
                                 random_state = RANDOM_STATE)
        clf.fit(X_train, y_train)

        scores = clf.predict_proba(X_test)[:, 1]
        y_pred = clf.predict(X_test)

        # per-patient scores — one row per patient
        for case_id, true_label, score in zip(case_ids[test_idx], y_test, scores):
            score_rows.append({
                "case_id":    case_id,
                "true_label": int(true_label),
                "score":      score,
            })

        # per-fold summary metrics
        try:
            auc = roc_auc_score(y_test, scores)
        except ValueError:
            auc = np.nan

        metric_rows.append({
            "fold":           fold,
            "macro-ovr-auc":  auc,
            "bacc":           balanced_accuracy_score(y_test, y_pred),
            "weighted_kappa": cohen_kappa_score(y_test, y_pred, weights = "linear"),
            "macro-f1":       f1_score(y_test, y_pred, average = "macro", zero_division = 0),
        })

        logger.info(
            f"    fold {fold:2d}: AUC = {auc:.3f}  "
            f"bACC = {metric_rows[-1]['bacc']:.3f}  "
            f"n_test = {len(test_idx)}"
        )

    return pd.DataFrame(score_rows), pd.DataFrame(metric_rows)


# ── output ────────────────────────────────────────────────────────────────────

def save_outputs(
    scores_df:  pd.DataFrame,
    metrics_df: pd.DataFrame,
    model:      str,
    dataset:    str,
    task:       str,
) -> None:
    """Save scores.csv and metrics.csv for a model/dataset/task combination."""
    out_dir = PREDICTIONS_DIR / model / dataset / task
    out_dir.mkdir(parents=True, exist_ok=True)

    scores_df.to_csv(out_dir / "scores.csv",   index=False)
    metrics_df.to_csv(out_dir / "metrics.csv", index=False)

    mean_auc  = metrics_df["macro-ovr-auc"].mean()
    mean_bacc = metrics_df["bacc"].mean()
    mean_f1   = metrics_df["macro-f1"].mean()
    mean_kap  = metrics_df["weighted_kappa"].mean()

    logger.info(
        f"  mean  AUC = {mean_auc:.3f}  bACC = {mean_bacc:.3f}  "
        f"F1 = {mean_f1:.3f}  κ = {mean_kap:.3f}"
    )
    logger.info(f"  → {out_dir}/scores.csv  ({len(scores_df)} patients)")


def main() -> None:
    for model in MODELS:
        for dataset, tasks in CONFOUNDING_TASKS.items():
            clinical_df = load_clinical(dataset)

            for task, label_col, label_map in tasks:
                logger.info(f"=== {model} / {dataset} / {task} ===")

                scores_path = PREDICTIONS_DIR / model / dataset / task / "scores.csv"
                if scores_path.exists():
                    logger.info(f"  already done, skipping")
                    continue

                X, y, case_ids = load_dataset(
                    model, dataset, label_col, label_map, clinical_df
                )

                if len(np.unique(y)) < 2:
                    logger.error(f"  only one class found — skipping")
                    continue

                scores_df, metrics_df = run_cv(X, y, case_ids)
                save_outputs(scores_df, metrics_df, model, dataset, task)

    logger.info("=== complete ===")


if __name__ == "__main__":
    main()

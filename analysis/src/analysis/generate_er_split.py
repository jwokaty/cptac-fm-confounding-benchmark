"""
generate_er_split.py

Generates a Patho-Bench-compatible split TSV and config.yaml for ER status
prediction in CPTAC-BRCA.

Uses the existing PIK3CA_mutation split as a template for:
  - case_id → slide_id mapping
  - fold assignments (50 stratified folds, case-level)

ER labels are loaded from the cBioPortal clinical file.
Patients with missing ER status are excluded.
Fold assignments are regenerated using stratified k-fold on the ER label
to ensure balanced positive/negative ratios across folds.

Output:
    analysis/splits/cptac_brca/ER_status/k=all.tsv
    analysis/splits/cptac_brca/ER_status/config.yaml

Usage:
    uv run python src/analysis/scripts/generate_er_split.py
"""

import yaml
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import StratifiedKFold

from analysis.config import DATA_DIR, SPLITS_DIR, LOGS_DIR
from analysis.utils import get_logger

logger = get_logger("generate_er_split", LOGS_DIR)

RANDOM_STATE = 42
N_FOLDS      = 10

PIKCA_TSV    = SPLITS_DIR / "cptac_brca" / "PIK3CA_mutation" / "k=all.tsv"
CLINICAL_TSV = DATA_DIR / "brca_cptac_2020_clinical_data.tsv"
OUTPUT_DIR   = SPLITS_DIR / "cptac_brca" / "ER_status"

LABEL_COL    = "ER Updated Clinical Status"
LABEL_MAP    = {"Positive": 1, "Negative": 0}


def load_slide_map(pikca_tsv: Path) -> pd.DataFrame:
    """
    Load case_id → slide_id mapping from existing PIK3CA split.
    Returns DataFrame with columns [case_id, slide_id].
    """
    df = pd.read_csv(pikca_tsv, sep="\t")
    return df[["case_id", "slide_id"]].copy()


def load_er_labels(clinical_tsv: Path) -> pd.DataFrame:
    """
    Load ER status labels from cBioPortal clinical file.
    Returns DataFrame with columns [case_id, ER_status].
    Drops patients with missing ER status.
    """
    df = pd.read_csv(clinical_tsv, sep="\t")
    df = df.rename(columns={"Patient ID": "case_id"})
    df["case_id"] = df["case_id"].str.lstrip("X")
    df = df[["case_id", LABEL_COL]].dropna(subset=[LABEL_COL])
    df = df[df[LABEL_COL].isin(LABEL_MAP.keys())]
    df["ER_status"] = df[LABEL_COL].map(LABEL_MAP)
    return df[["case_id", "ER_status"]].reset_index(drop=True)


def generate_folds(case_labels: pd.DataFrame, n_folds: int) -> pd.DataFrame:
    """
    Generate stratified k-fold assignments at case level.

    Args:
        case_labels: DataFrame with columns [case_id, ER_status]
        n_folds:     number of folds

    Returns:
        DataFrame with case_id and fold_0 ... fold_{n_folds-1} columns
    """
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=RANDOM_STATE)
    fold_assignments = pd.DataFrame(index=case_labels.index)
    fold_assignments["case_id"] = case_labels["case_id"]

    X = np.zeros(len(case_labels))
    y = case_labels["ER_status"].values

    for fold_idx, (train_idx, test_idx) in enumerate(skf.split(X, y)):
        col = f"fold_{fold_idx}"
        fold_assignments[col] = "train"
        fold_assignments.loc[test_idx, col] = "test"

    return fold_assignments


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("loading slide map from PIK3CA split...")
    slide_map = load_slide_map(PIKCA_TSV)
    logger.info(f"  {len(slide_map)} slides, {slide_map['case_id'].nunique()} cases")

    logger.info("loading ER labels from clinical file...")
    er_labels = load_er_labels(CLINICAL_TSV)
    logger.info(f"  {len(er_labels)} cases with ER status")
    logger.info(f"  positive: {er_labels['ER_status'].sum()}, negative: {(er_labels['ER_status']==0).sum()}")

    logger.info("generating fold assignments...")
    folds = generate_folds(er_labels, N_FOLDS)

    logger.info("merging slide map with ER labels and folds...")
    df = slide_map.merge(er_labels[["case_id", "ER_status"]], on="case_id", how="inner")
    df = df.merge(folds, on="case_id", how="inner")
    df = df.rename(columns={"ER_status": "ER_status"})

    logger.info(f"  final: {len(df)} slides, {df['case_id'].nunique()} cases")

    # save TSV
    tsv_path = OUTPUT_DIR / "k=all.tsv"
    df.to_csv(tsv_path, sep="\t", index=False)
    logger.info(f"  saved to {tsv_path}")

    # save config.yaml
    config = {
        "datasets": ["cptac_brca"],
        "extra_cols": [],
        "label_dict": {0: "negative", 1: "positive"},
        "metrics": ["macro-ovr-auc"],
        "num_samples": int(df["case_id"].nunique()),
        "sample_col": "case_id",
        "task_col": "ER_status",
        "task_type": "classification",
    }
    config_path = OUTPUT_DIR / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    logger.info(f"  saved to {config_path}")

    logger.info("=== complete ===")


if __name__ == "__main__":
    main()

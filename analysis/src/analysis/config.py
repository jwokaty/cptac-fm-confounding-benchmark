"""
config.py

Shared configuration for the analysis project.
"""

from pathlib import Path

BASE = Path(__file__).parents[3]

OUTPUTS_DIR = BASE / "extraction" / "outputs"
SPLITS_DIR  = BASE / "analysis" / "splits"
RESULTS_DIR = BASE / "analysis" / "results"
LIB_DIR    = BASE / "analysis" / "lib"
LOGS_DIR    = BASE / "analysis" / "logs"
PREDICTIONS_DIR   = RESULTS_DIR / "predictions"
CONFOUNDING_DIR   = RESULTS_DIR / "confounding"
DATA_DIR          = BASE / "analysis" / "data" 

FDR_ALPHA         = 0.10
N_FOLDS           = 10
PERM_RUNS         = 10_000
RANDOM_STATE      = 42

MODELS = ["titan", "mstar", "provgigapath", "uni2h"]

TASKS = {
    "cptac_brca": [
        "PIK3CA_mutation",
        "TP53_mutation",
        "Immune_class",
        "ER_status",
    ],
    "cptac_ucec": [
        "PTEN_mutation",
        "CTNNB1_mutation",
        "Immune_class",
    ],
}

COLLECTIONS = {
    "titan": {
        "cptac_brca": OUTPUTS_DIR / "titan" / "cptac_brca" / "20x_512px_0px_overlap" / "slide_features_titan",
        "cptac_ucec": OUTPUTS_DIR / "titan" / "cptac_ucec" / "20x_512px_0px_overlap" / "slide_features_titan",
    },
    "mstar": {
        "cptac_brca": OUTPUTS_DIR / "mstar" / "cptac_brca",
        "cptac_ucec": OUTPUTS_DIR / "mstar" / "cptac_ucec",
    },
    "provgigapath": {
        "cptac_brca": OUTPUTS_DIR / "provgigapath" / "cptac_brca" / "20x_256px_0px_overlap" / "slide_features_gigapath",
        "cptac_ucec": OUTPUTS_DIR / "provgigapath" / "cptac_ucec" / "20x_256px_0px_overlap" / "slide_features_gigapath",
    },
    "uni2h": {
        "cptac_brca": OUTPUTS_DIR / "uni2h" / "cptac_brca",
        "cptac_ucec": OUTPUTS_DIR / "uni2h" / "cptac_ucec",
    },
}

CLINICAL_FILES = {
    "cptac_brca": DATA_DIR / "brca_cptac_2020_clinical_data.tsv",
    "cptac_ucec": DATA_DIR / "ucec_cptac_2020_clinical_data.tsv",
}

# tasks for confounding analysis
# each entry: dataset → list of (task_name, label_col, label_map)
# label_map: dict mapping raw clinical values to 0/1, or None if already 0/1
CONFOUNDING_TASKS = {
    "cptac_brca": [
        (
            "ER_status",
            "ER Updated Clinical Status",
            {"Negative": 0, "Positive": 1},
        ),
    ],
    "cptac_ucec": [
        (
            "PTEN_mutation",
            "PI3K PTEN",
            None,  # already 0/1 in clinical file
        ),
    ],
}

# tasks and their stratifying variables
# each entry: dataset → list of (task_name, stratifier_col, stratifier_name)
STRATIFIED_TASKS = {
    "cptac_brca": [
        (
            "ER_status",
            "PAM50",
            "PAM50",
        ),
    ],
    "cptac_ucec": [
        (
            "PTEN_mutation",
            "MSI Status",
            "MSI_status",
        ),
        (
            "PTEN_mutation",
            "TMB_group",
            "TMB",
        ),
    ],
}


EMBEDDINGS = {
    "titan": {
        "cptac_brca": OUTPUTS_DIR / "titan" / "by_case_id" / "cptac_brca",
        "cptac_ucec": OUTPUTS_DIR / "titan" / "by_case_id" / "cptac_ucec",
    },
    "mstar": {
        "cptac_brca": OUTPUTS_DIR / "mstar" / "by_case_id" / "cptac_brca",
        "cptac_ucec": OUTPUTS_DIR / "mstar" / "by_case_id" / "cptac_ucec",
    },
    "provgigapath": {
        "cptac_brca": OUTPUTS_DIR / "provgigapath" / "by_case_id" / "cptac_brca",
        "cptac_ucec": OUTPUTS_DIR / "provgigapath" / "by_case_id" / "cptac_ucec",
    },
    "uni2h": {
        "cptac_brca": OUTPUTS_DIR / "uni2h" / "by_case_id" / "cptac_brca",
        "cptac_ucec": OUTPUTS_DIR / "uni2h" / "by_case_id" / "cptac_ucec",
    },
}

TMB_FILES = {
    "cptac_ucec": DATA_DIR / "pten_tmb.tsv"
}

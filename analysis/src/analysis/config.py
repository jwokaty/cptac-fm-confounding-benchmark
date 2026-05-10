"""
config.py

Shared configuration for the analysis project.
"""

from pathlib import Path

BASE = Path(__file__).parents[3]

OUTPUTS_DIR = BASE / "extraction" / "outputs"
SPLITS_DIR  = BASE / "analysis" / "splits"
RESULTS_DIR = BASE / "analysis" / "results"
LOGS_DIR    = BASE / "analysis" / "logs"

MODELS = ["titan", "mstar"]

TASKS = {
    "cptac_brca": [
        "PIK3CA_mutation",
        "TP53_mutation",
        "Immune_class",
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
}

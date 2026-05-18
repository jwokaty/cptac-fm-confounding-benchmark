"""
pten_tmb.py

Generates the TMB using getTMB from https://github.com/imuhdawood/HistBiases
and data_mutations.txt in https://datahub.assets.cbioportal.org/ucec_cptac_2020.tar.gz

Instructions:
    uv run python src/analysis/scripts/pten_tmb.py

Input: data_mutations.txt from ucec_cptac_2020
Output: analysis/results/pten_tmb.tsv

Usage:
    uv run python src/analysis/scripts/pten_tmb.py
"""

import io
import sys
import tarfile
import zipfile
from pathlib import Path

import requests

from analysis.config import DATA_DIR, LIB_DIR, LOGS_DIR
from analysis.utils import get_logger

logger = get_logger("pten_tmb", LOGS_DIR)


def get_repo_data() -> None:
    # download HistBiases repo
    logger.info("Downloading HistBiases repo...")
    response = requests.get("https://github.com/imuhdawood/HistBiases/archive/refs/heads/main.zip")
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        logger.info(f"Extracting to {LIB_DIR}")
        z.extractall(LIB_DIR)

    # download cBioPortal study data
    logger.info("Downloading ucec_cptac_2020...")
    response = requests.get("https://datahub.assets.cbioportal.org/ucec_cptac_2020.tar.gz")
    with tarfile.open(fileobj = io.BytesIO(response.content), mode = 'r:gz') as t:
        logger.info(f"Extracting to {DATA_DIR}")
        t.extractall(DATA_DIR)


def get_tmb() -> None:
    sys.path.append(str(LIB_DIR / "HistBiases-main"))
    from application.confounder_analysis.tmb import getTMB

    sample_tmb_map = getTMB(
        str(DATA_DIR / "ucec_cptac_2020"),
        ignoreGenes = ["PTEN"],
        cohort = "cptac",
        tissueType = "ucec",
    )

    saveto = DATA_DIR / "pten_tmb.tsv"
    saveto.parent.mkdir(parents = True, exist_ok = True)
    sample_tmb_map.to_csv(str(saveto), sep = "\t")
    logger.info(f"saved to {saveto}")
    return sample_tmb_map


def main() -> None:
    get_repo_data()
    get_tmb()
    logger.info("=== complete ===")


if __name__ == "__main__":
    main()

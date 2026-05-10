"""
fetch_splits.py

Downloads Patho-Bench split TSVs and task configs from HuggingFace.
Requires HF_TOKEN in .env with access to MahmoodLab/Patho-Bench.

Usage:
    uv run python src/analysis/scripts/fetch_splits.py
"""

import os
from dotenv import load_dotenv
import datasets

from analysis.config import SPLITS_DIR, TASKS, LOGS_DIR
from analysis.utils import get_logger


load_dotenv()
logger = get_logger("fetch_splits", LOGS_DIR)


def main() -> None:
    token = os.getenv("HF_TOKEN")
    if not token:
        logger.error("HF_TOKEN not set in .env")
        raise SystemExit(1)

    for dataset in TASKS.keys():
        logger.info(f"downloading splits for {dataset}...")
        datasets.load_dataset(
            "MahmoodLab/Patho-Bench",
            cache_dir = str(SPLITS_DIR),
            dataset_to_download = dataset,
            task_in_dataset = "*",
            trust_remote_code = True
        )
        logger.info(f"  done: {dataset}")

    logger.info("all splits downloaded")
    logger.info(f"splits saved to {SPLITS_DIR}")


if __name__ == "__main__":
    main()

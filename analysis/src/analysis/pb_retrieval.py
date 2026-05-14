"""
pb_retrieval.py

Runs Patho-Bench retrieval experiments for TITAN and mSTAR on CPTAC tasks.

Iterates over all combinations of models (TITAN, mSTAR) and tasks defined in
config.py.

Splits must be downloaded first by running fetch_splits.py. Embeddings must be
aggregated to case level first by running pool_to_case_id.py.

Results are saved as JSON to:
    analysis/results/retrieval/{model}/{dataset}/{task}/{model}_retrieval/{value}

Usage:
    uv run python src/analysis/pb_retrieval.py
"""

import json
import os
from pathlib import Path

from patho_bench.ExperimentFactory import ExperimentFactory

from analysis.config import EMBEDDINGS, LOGS_DIR, MODELS, RESULTS_DIR, SPLITS_DIR, TASKS
from analysis.utils import get_logger

logger = get_logger("pb_retrieval", LOGS_DIR)


def r_experiment(model: str, dataset: str, task: str) -> None:
    """
    Run a Patho-Bench retrieval for a single model/dataset/task.

    Args:
        model:   model name, one of "titan" or "mstar"
        dataset: dataset name, one of "cptac_brca" or "cptac_ucec"
        task:    task name, e.g. "PIK3CA_mutation" or "Immune_class"

    Raises:
        FileNotFoundError: if the split or config file does not exist locally.
            Run fetch_splits.py first.
        FileNotFoundError: if the embeddings directory does not exist.
            Run pool_to_case_id.py first.
    """
    split_path = SPLITS_DIR / dataset / task / "k=all.tsv"
    config_path = SPLITS_DIR / dataset / task / "config.yaml"
    saveto = RESULTS_DIR / "retrieval" / model / dataset / task

    if not split_path.exists():
        raise FileNotFoundError(
            f"split not found at {split_path} — run fetch_splits.py first"
        )
    if not config_path.exists():
        raise FileNotFoundError(
            f"config not found at {config_path} — run fetch_splits.py first"
        )

    embeddings_dir = EMBEDDINGS[model][dataset]
    if not embeddings_dir.exists():
        raise FileNotFoundError(
            f"no embeddings at {embeddings_dir} — run pool_to_case_id.py first"
        )

    experiment = ExperimentFactory.retrieval(
        split = str(split_path),
        task_config = str(config_path),
        pooled_embeddings_dir = str(embeddings_dir),
        saveto = str(saveto),
        combine_slides_per_patient = False,
        similarity = "l2",
        model_name = model,
        centering = False,
    )

    experiment.train()
    experiment.test()
    result = experiment.report_results(metric = 'mAP@1')
    logger.info("===mAP@1===")
    logger.info(result)
    result = experiment.report_results(metric = 'mAP@5')
    logger.info("===mAP@5===")
    logger.info(result)
    result = experiment.report_results(metric = 'mAP@10')
    logger.info("===mAP@10===")
    logger.info(result)

    return result

def is_complete(model: str, dataset: str, task: str) -> bool:
    """
    Check whether retrieval has completed.

    Args:
        model:   model name
        dataset: dataset name
        task:    task name

    Returns:
        True if results directory has files.
    """
    saveto = RESULTS_DIR / "retrieval" / model / dataset / task
    if not saveto.exists():
        return False
    return len(os.listdir(saveto)) > 0


def main() -> None:
    for model in MODELS:
        for dataset, tasks in TASKS.items():
            for task in tasks:
                logger.info(f"=== {model} / {dataset} / {task} ===")
                if is_complete(model, dataset, task):
                    logger.info(f"  skipping — already complete")
                    continue
                try:
                    r_experiment(model, dataset, task)
                except Exception as e:
                    logger.error(f"  failed: {e}")
                    raise

if __name__ == "__main__":
    main()

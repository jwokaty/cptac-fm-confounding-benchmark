"""
pb_linprobe.py

Runs Patho-Bench linear probe experiments for TITAN and mSTAR on CPTAC tasks.

Iterates over all combinations of models (TITAN, mSTAR) and tasks defined in
config.py. For each combination, runs a cost sweep using logistic regression
linear probing with pre-pooled case-level slide embeddings, evaluated on
held-out test folds.

Splits must be downloaded first by running fetch_splits.py. Embeddings must be
aggregated to case level first by running pool_to_case_id.py.

Results are saved as JSON to:
    analysis/results/linprobe/{model}/{dataset}/{task}/{model}_linprobe/cost={value}/

The script can be stopped and restarted safely — any cost value that already
has a test_metrics_summary.json will be skipped.

Usage:
    uv run python src/analysis/pb_linprobe.py
"""

import json
from pathlib import Path

from patho_bench.ExperimentFactory import ExperimentFactory

from analysis.config import EMBEDDINGS, LOGS_DIR, MODELS, RESULTS_DIR, SPLITS_DIR, TASKS
from analysis.utils import get_logger

logger = get_logger("pb_linprobe", LOGS_DIR)


def lp_experiment(model: str, dataset: str, task: str) -> None:
    """
    Run a Patho-Bench linear probe cost sweep for a single model/dataset/task.

    Runs 45 logistic regression experiments across a log-scale range of
    regularization strengths (cost='auto'). Results for each cost value are
    saved to a separate subdirectory under saveto_root.

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
    saveto = RESULTS_DIR / "linprobe" / model / dataset / task

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

    ExperimentFactory.sweep(
        experiment_type="linprobe",
        split=str(split_path),
        task_config=str(config_path),
        pooled_embeddings_dir=str(embeddings_dir),
        saveto_root=str(saveto),
        combine_slides_per_patient=False,
        sweep_over={"COST": "auto"},
        model_name=model,
    )


def get_cost_dirs(model: str, dataset: str, task: str) -> list[Path]:
    """
    Return all cost subdirectories that have completed results.

    Args:
        model:   model name
        dataset: dataset name
        task:    task name

    Returns:
        List of Path objects for each cost directory with a
        test_metrics_summary.json file.
    """
    sweep_dir = RESULTS_DIR / "linprobe" / model / dataset / task / f"{model}_linprobe"
    if not sweep_dir.exists():
        return []
    return [
        d for d in sweep_dir.iterdir()
        if d.is_dir() and (d / "test_metrics_summary.json").exists()
    ]


def is_complete(model: str, dataset: str, task: str) -> bool:
    """
    Check whether the cost sweep has completed all 45 cost values.

    Args:
        model:   model name
        dataset: dataset name
        task:    task name

    Returns:
        True if all 45 cost directories have test_metrics_summary.json.
    """
    return len(get_cost_dirs(model, dataset, task)) == 45


def read_best_results(model: str, dataset: str, task: str) -> tuple[dict, str]:
    """
    Read results from the best cost value in a completed sweep.

    Best is defined as the cost value with the highest macro-ovr-auc mean.

    Args:
        model:   model name
        dataset: dataset name
        task:    task name

    Returns:
        Tuple of (metrics dict, cost string) for the best cost value.
    """
    cost_dirs = get_cost_dirs(model, dataset, task)
    best_results, best_auc, best_cost = None, -1, None

    for d in cost_dirs:
        with open(d / "test_metrics_summary.json") as f:
            results = json.load(f)
        auc = results["macro-ovr-auc"]["mean"]
        if auc > best_auc:
            best_auc = auc
            best_results = results
            best_cost = d.name

    return best_results, best_cost


def main() -> None:
    for model in MODELS:
        for dataset, tasks in TASKS.items():
            for task in tasks:
                if is_complete(model, dataset, task):
                    logger.info(f"skipping {model}/{dataset}/{task} — already complete")
                    results, cost = read_best_results(model, dataset, task)
                    logger.info(f"  best {cost} — macro-ovr-auc: {results['macro-ovr-auc']['formatted']}")
                    continue

                logger.info(f"=== {model} / {dataset} / {task} ===")
                try:
                    lp_experiment(model, dataset, task)
                    results, cost = read_best_results(model, dataset, task)
                    logger.info(f"  best {cost} — macro-ovr-auc: {results['macro-ovr-auc']['formatted']}")
                except Exception as e:
                    logger.error(f"  failed: {e}")
                    raise


if __name__ == "__main__":
    main()

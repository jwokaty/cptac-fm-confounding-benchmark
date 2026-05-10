"""
pool_to_case_id.py

Aggregates slide-level embeddings to patient-level embeddings by mean pooling
all slides belonging to the same case ID.

Input:  slide-level .h5 files named by slide_id
Output: case-level .h5 files named by case_id, saved to by_case_id/ directories

Usage:
    uv run python src/analysis/scripts/pool_to_case_id.py

Output structure:
    extraction/outputs/titan/by_case_id/cptac_brca/
    extraction/outputs/titan/by_case_id/cptac_ucec/
    extraction/outputs/mstar/by_case_id/cptac_brca/
    extraction/outputs/mstar/by_case_id/cptac_ucec/
"""

from collections import defaultdict
from pathlib import Path
import re

import h5py
import numpy as np

from analysis.config import COLLECTIONS, LOGS_DIR, OUTPUTS_DIR
from analysis.utils import get_logger


logger = get_logger("pool_to_case_id", LOGS_DIR)

UCEC_PATTERN = re.compile(r"^(C3[LN]-\d{5})-\d+")
UUID_SEGMENT = re.compile(r"^[0-9a-f]{8}$")
PURE_NUMERIC = re.compile(r"^\d+$")


def extract_case_id(stem: str) -> str:
    """
    Extract case ID from a slide filename stem.

    UCEC examples:
        C3L-00449-21       → C3L-00449
        C3N-01847-23       → C3N-01847

    BRCA examples:
        01BR033-3329b802-e49f-4494-b645-868a25    → 01BR033
        03BR012-2d8514b6-c01a-4166-a0c1-bc7012_3 → 03BR012
    """
    stem = re.sub(r"_\d+$", "", stem)

    m = UCEC_PATTERN.match(stem)
    if m:
        return m.group(1)

    tokens = stem.split("-")
    case_tokens = []
    for token in tokens:
        if UUID_SEGMENT.match(token) or PURE_NUMERIC.match(token):
            break
        case_tokens.append(token)

    if not case_tokens:
        raise ValueError(f"could not extract case ID from stem: {stem!r}")

    return "-".join(case_tokens)


def load_embedding(h5_path: Path) -> np.ndarray:
    """Load a 1-D feature vector from an h5 file."""
    with h5py.File(h5_path, "r") as f:
        features = f["features"][:]
    if features.ndim != 1:
        raise ValueError(f"expected 1-D features, got shape {features.shape} in {h5_path}")
    return features


def save_embedding(embedding: np.ndarray, case_id: str, output_dir: Path) -> Path:
    """Save a 1-D feature vector as {case_id}.h5 with a features key."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{case_id}.h5"
    with h5py.File(output_path, "w") as f:
        f.create_dataset("features", data=embedding[np.newaxis, :])
    return output_path


def pool_collection(slide_dir: Path, output_dir: Path) -> None:
    """
    Mean pool slide-level embeddings to case-level embeddings.

    For patients with a single slide, the embedding is copied as-is.
    For patients with multiple slides, embeddings are mean pooled.

    Args:
        slide_dir:  directory containing slide-level .h5 files
        output_dir: directory to write case-level .h5 files
    """
    h5_files = sorted(slide_dir.glob("*.h5"))
    if not h5_files:
        logger.error(f"no .h5 files found in {slide_dir}")
        return

    logger.info(f"found {len(h5_files)} slides in {slide_dir}")

    case_slides: dict[str, list[Path]] = defaultdict(list)
    for h5_path in h5_files:
        try:
            case_id = extract_case_id(h5_path.stem)
        except ValueError as e:
            logger.error(f"  skipping {h5_path.name}: {e}")
            continue
        case_slides[case_id].append(h5_path)

    logger.info(f"  → {len(case_slides)} unique case IDs")

    multi = {k: v for k, v in case_slides.items() if len(v) > 1}
    if multi:
        logger.info(f"  → {len(multi)} cases with multiple slides (will be mean pooled):")
        for case_id, paths in sorted(multi.items()):
            logger.info(f"    {case_id}: {[p.name for p in paths]}")

    done, failed = 0, []

    for case_id, paths in sorted(case_slides.items()):
        output_path = output_dir / f"{case_id}.h5"
        if output_path.exists():
            logger.info(f"  skipping {case_id} — already exists")
            done += 1
            continue

        try:
            embeddings = np.stack([load_embedding(p) for p in paths])
            case_embedding = embeddings.mean(axis=0)
            save_embedding(case_embedding, case_id, output_dir)
            done += 1
            logger.info(f"  {case_id} → shape {case_embedding.shape} (from {len(paths)} slide(s))")
        except Exception as e:
            logger.error(f"  {case_id} failed: {e}")
            failed.append(case_id)

    logger.info(f"done: {done}, failed: {len(failed)}")
    if failed:
        logger.error(f"failed cases: {failed}")


def main() -> None:
    for model, collections in COLLECTIONS.items():
        for dataset, slide_dir in collections.items():
            output_dir = OUTPUTS_DIR / model / "by_case_id" / dataset
            logger.info(f"=== {model.upper()} / {dataset} ===")
            logger.info(f"  input:  {slide_dir}")
            logger.info(f"  output: {output_dir}")
            if not slide_dir.exists():
                logger.error(f"  input directory not found — skipping")
                continue
            pool_collection(slide_dir, output_dir)
    logger.info("=== complete ===")


if __name__ == "__main__":
    main()

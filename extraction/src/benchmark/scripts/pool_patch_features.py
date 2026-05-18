"""
pool_patch_features.py

Mean pools patch-level features into slide-level embeddings for mSTAR and UNI2-h.

mSTAR:  reads .h5 files with shape (num_patches, embed_dim)
UNI2-h: reads .h5 files with shape (1, num_patches, 1536) — leading dim is squeezed

Output: one .h5 file per slide saved to slide_embeddings/{model}/cptac_{dataset}/

Usage:
    uv run python src/benchmark/scripts/pool_patch_features.py --model mstar
    uv run python src/benchmark/scripts/pool_patch_features.py --model uni2h
    uv run python src/benchmark/scripts/pool_patch_features.py --model all
"""

import argparse
import sys
import torch
import h5py
from pathlib import Path
from dotenv import load_dotenv

from benchmark.paths import (
    MSTAR_PATCH_BRCA_DIR,
    MSTAR_PATCH_UCEC_DIR,
    MSTAR_BRCA_DIR,
    MSTAR_UCEC_DIR,
    UNI2H_PATCH_BRCA_DIR,
    UNI2H_PATCH_UCEC_DIR,
    UNI2H_BRCA_DIR,
    UNI2H_UCEC_DIR,
    create_all_dirs,
)
from benchmark.utils import (
    get_logger,
    save_slide_embedding,
    iter_h5_slides,
)

load_dotenv()
logger = get_logger("pool_patch_features")


def load_h5_patch_features(h5_path: Path, squeeze: bool = False) -> torch.Tensor:
    """
    Load patch features from an .h5 file.

    Args:
        h5_path: path to .h5 file
        squeeze: if True, squeeze leading dimension (for UNI2-h shape (1, num_patches, embed_dim))

    Returns:
        features: (num_patches, embed_dim) tensor
    """
    with h5py.File(h5_path, "r") as f:
        features = torch.from_numpy(f["features"][:])
    if squeeze:
        features = features.squeeze(0)
    if features.ndim != 2:
        raise ValueError(f"expected 2D features after loading, got shape {features.shape} in {h5_path}")
    return features


def pool_collection(
    h5_dir: Path,
    output_dir: Path,
    squeeze: bool = False,
) -> None:
    """
    Mean pool patch features into slide embeddings.

    Loads each .h5 file, averages across all patches,
    saves one slide embedding .h5 file per slide to output_dir.

    Args:
        h5_dir:    directory containing patch-level .h5 files
        output_dir: directory to save slide-level .h5 files
        squeeze:   whether to squeeze leading dimension (True for UNI2-h)
    """
    h5_files = list(h5_dir.glob("*.h5"))
    if not h5_files:
        logger.error(f"no .h5 files found in {h5_dir}")
        sys.exit(1)

    logger.info(f"found {len(h5_files)} slides in {h5_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    done = 0
    failed = []

    for slide_id, h5_path in iter_h5_slides(h5_dir):
        output_path = output_dir / f"{slide_id}.h5"

        if output_path.exists():
            logger.info(f"  skipping {slide_id} — already pooled")
            done += 1
            continue

        try:
            # load patch features — shape: (num_patches, embed_dim)
            features = load_h5_patch_features(h5_path, squeeze=squeeze)

            # mean pool across all patches → shape: (embed_dim,)
            slide_embedding = features.mean(dim=0)

            save_slide_embedding(slide_embedding, slide_id, output_dir)
            done += 1
            logger.info(f"  {slide_id} → {slide_embedding.shape}")

        except Exception as e:
            logger.error(f"  {slide_id} failed: {e}")
            failed.append(slide_id)

    logger.info(f"done: {done}, failed: {len(failed)}")
    if failed:
        logger.error(f"failed slides: {failed}")


def pool_mstar() -> None:
    """Mean pool mSTAR patch features for both datasets."""
    logger.info("=== mSTAR: pooling CPTAC-BRCA ===")
    pool_collection(MSTAR_PATCH_BRCA_DIR, MSTAR_BRCA_DIR, squeeze=False)

    logger.info("=== mSTAR: pooling CPTAC-UCEC ===")
    pool_collection(MSTAR_PATCH_UCEC_DIR, MSTAR_UCEC_DIR, squeeze=False)

    logger.info("mSTAR pooling complete")
    logger.info(f"  embeddings saved to: {MSTAR_BRCA_DIR}")
    logger.info(f"  embeddings saved to: {MSTAR_UCEC_DIR}")


def pool_uni2h() -> None:
    """Mean pool UNI2-h patch features for both datasets."""
    logger.info("=== UNI2-h: pooling CPTAC-BRCA ===")
    pool_collection(UNI2H_PATCH_BRCA_DIR, UNI2H_BRCA_DIR, squeeze=True)

    logger.info("=== UNI2-h: pooling CPTAC-UCEC ===")
    pool_collection(UNI2H_PATCH_UCEC_DIR, UNI2H_UCEC_DIR, squeeze=True)

    logger.info("UNI2-h pooling complete")
    logger.info(f"  embeddings saved to: {UNI2H_BRCA_DIR}")
    logger.info(f"  embeddings saved to: {UNI2H_UCEC_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mean pool patch features into slide embeddings")
    parser.add_argument(
        "--model",
        choices=["mstar", "uni2h", "all"],
        default="all",
        help="which model to pool (default: all)",
    )
    args = parser.parse_args()

    create_all_dirs()

    if args.model in ("mstar", "all"):
        pool_mstar()

    if args.model in ("uni2h", "all"):
        pool_uni2h()


if __name__ == "__main__":
    main()

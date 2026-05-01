import sys
import torch
from pathlib import Path
from dotenv import load_dotenv

from benchmark.paths import (
    MSTAR_BRCA_PT_DIR,
    MSTAR_UCEC_PT_DIR,
    MSTAR_BRCA_DIR,
    MSTAR_UCEC_DIR,
    create_all_dirs,
)
from benchmark.utils import (
    get_logger,
    load_pt_features,
    save_slide_embedding,
    iter_pt_slides,
)

load_dotenv()
logger = get_logger("pool_mstar")


def pool_collection(
    pt_dir: Path,
    output_dir: Path,
) -> None:
    """
    Mean pool mSTAR patch features into slide embeddings.
    Loads each .pt file, averages across all patches,
    saves one slide embedding .h5 file per slide to output_dir.
    """
    pt_files = list(pt_dir.glob("*.pt"))
    if not pt_files:
        logger.error(f"no .pt files found in {pt_dir}")
        sys.exit(1)

    logger.info(f"found {len(pt_files)} slides in {pt_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    done = 0
    failed = []

    for slide_id, pt_path in iter_pt_slides(pt_dir):
        output_path = output_dir / f"{slide_id}.h5"

        if output_path.exists():
            logger.info(f"  skipping {slide_id} — already pooled")
            done += 1
            continue

        try:
            # load patch features — shape: (num_patches, embed_dim)
            features = load_pt_features(pt_path)

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


def main() -> None:
    create_all_dirs()

    # mean pooling is CPU-only — no GPU needed
    logger.info("pooling CPTAC-BRCA...")
    pool_collection(MSTAR_BRCA_PT_DIR, MSTAR_BRCA_DIR)

    logger.info("pooling CPTAC-UCEC...")
    pool_collection(MSTAR_UCEC_PT_DIR, MSTAR_UCEC_DIR)

    logger.info("mSTAR pooling complete")
    logger.info(f"embeddings saved to:")
    logger.info(f"  {MSTAR_BRCA_DIR}")
    logger.info(f"  {MSTAR_UCEC_DIR}")


if __name__ == "__main__":
    main()

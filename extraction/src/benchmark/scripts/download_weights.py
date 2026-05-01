import os
import sys
from dotenv import load_dotenv
from huggingface_hub import login, hf_hub_download

from benchmark.paths import MSTAR_WEIGHTS_PATH, WEIGHTS_DIR, create_all_dirs
from benchmark.utils import get_logger

load_dotenv()
logger = get_logger("download_weights")


def main() -> None:
    token = os.getenv("HF_TOKEN")
    if not token:
        logger.error("HF_TOKEN not set in .env")
        sys.exit(1)

    logger.info("creating directories...")
    create_all_dirs()

    logger.info("logging into HuggingFace...")
    login(token=token)

    if MSTAR_WEIGHTS_PATH.exists():
        logger.info(f"mSTAR weights already exist at {MSTAR_WEIGHTS_PATH}, skipping")
    else:
        logger.info("downloading mSTAR weights...")
        hf_hub_download(
            repo_id="Wangyh/mSTAR",
            filename="mSTAR.pth",
            local_dir=WEIGHTS_DIR,
            token=token,
        )
        logger.info(f"mSTAR weights saved to {MSTAR_WEIGHTS_PATH}")

    logger.info("done — TITAN and CONCH v1.5 will be downloaded automatically by TRIDENT")


if __name__ == "__main__":
    main()

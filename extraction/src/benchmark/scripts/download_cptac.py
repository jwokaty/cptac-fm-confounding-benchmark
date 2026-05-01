import os
import sys
import subprocess
from pathlib import Path

from dotenv import load_dotenv

from benchmark.paths import (
    BRCA_SLIDES_DIR,
    UCEC_SLIDES_DIR,
    BRCA_CSV,
    UCEC_CSV,
    create_all_dirs,
)
from benchmark.utils import get_logger, generate_dataset_csv

load_dotenv()
logger = get_logger("download_cptac")


COLLECTIONS = {
    "CPTAC-BRCA": {
        "slides_dir": BRCA_SLIDES_DIR,
        "csv_path":   BRCA_CSV,
        "env_var":    "ASPERA_URL_CPTAC_BRCA",
    },
    "CPTAC-UCEC": {
        "slides_dir": UCEC_SLIDES_DIR,
        "csv_path":   UCEC_CSV,
        "env_var":    "ASPERA_URL_CPTAC_UCEC",
    },
}


def already_downloaded(slides_dir: Path) -> int:
    """Return count of slides already present in a directory."""
    return len(
        list(slides_dir.glob("*.svs")) +
        list(slides_dir.glob("*.tiff")) +
        list(slides_dir.glob("*.tif"))
    )


def download_via_aspera(aspera_url: str, slides_dir: Path) -> None:
    """Download a CPTAC collection via ascli faspex5."""
    logger.info(f"downloading via Aspera to {slides_dir}...")
    cmd = [
        "ascli", "faspex5", "packages", "receive",
        f"--url={aspera_url}",
        f"--to-folder={slides_dir}",
    ]
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error(f"ascli failed:\n{e.stderr}")
        raise
    except FileNotFoundError:
        logger.error(
            "ascli not found — install it first:\n"
            "gem install aspera-cli\n"
            "ascli config ascp install"
        )
        raise


def download_collection(name: str, config: dict) -> None:
    slides_dir = config["slides_dir"]
    slides_dir.mkdir(parents=True, exist_ok=True)

    n = already_downloaded(slides_dir)
    if n > 0:
        logger.info(f"{name} — {n} slides already present, skipping download")
    else:
        aspera_url = os.getenv(config["env_var"])
        if not aspera_url:
            raise ValueError(
                f"{config['env_var']} not set in .env\n"
                f"go to the TCIA collection page, right-click the Download "
                f"button, copy link address, paste into .env"
            )
        download_via_aspera(aspera_url, slides_dir)

    n = generate_dataset_csv(slides_dir, config["csv_path"], logger=logger)
    logger.info(f"{name} — {n} slides written to {config['csv_path']}")


def main() -> None:
    logger.info("creating directories...")
    create_all_dirs()

    failed = []
    for name, config in COLLECTIONS.items():
        try:
            download_collection(name, config)
        except Exception as e:
            logger.error(f"{name} failed: {e}")
            failed.append(name)

    if failed:
        logger.error(f"failed collections: {failed}")
        sys.exit(1)

    logger.info("all collections downloaded successfully")


if __name__ == "__main__":
    main()

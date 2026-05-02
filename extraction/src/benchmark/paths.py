from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# root
# on Vast.ai set DATA_DIR=/data in .env
# locally defaults to data/ inside the project
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

# slides
SLIDES_DIR      = DATA_DIR / "slides"
BRCA_SLIDES_SUBDIR = os.getenv("BRCA_SLIDES_SUBDIR", "")
UCEC_SLIDES_SUBDIR = os.getenv("UCEC_SLIDES_SUBDIR", "")
BRCA_SLIDES_DIR = SLIDES_DIR / "cptac_brca" / BRCA_SLIDES_SUBDIR if BRCA_SLIDES_SUBDIR else SLIDES_DIR / "cptac_brca"
UCEC_SLIDES_DIR = SLIDES_DIR / "cptac_ucec" / UCEC_SLIDES_SUBDIR if UCEC_SLIDES_SUBDIR else SLIDES_DIR / "cptac_ucec"

# trident outputs — TITAN pipeline
# TRIDENT names subdirectories automatically based on mag and patch_size
# --mag 20 --patch_size 512 → 20x_512px/
TRIDENT_DIR          = DATA_DIR / "trident"
TRIDENT_BRCA_DIR     = TRIDENT_DIR / "cptac_brca"
TRIDENT_UCEC_DIR     = TRIDENT_DIR / "cptac_ucec"

# patch coords
TRIDENT_BRCA_COORDS_DIR = TRIDENT_BRCA_DIR / "20x_512px" / "patches"
TRIDENT_UCEC_COORDS_DIR = TRIDENT_UCEC_DIR / "20x_512px" / "patches"

# conch v1.5 patch features
TRIDENT_BRCA_FEATS_DIR  = TRIDENT_BRCA_DIR / "20x_512px" / "features_conch_v15"
TRIDENT_UCEC_FEATS_DIR  = TRIDENT_UCEC_DIR / "20x_512px" / "features_conch_v15"

# titan slide embeddings — one .h5 file per slide
TITAN_BRCA_DIR = TRIDENT_BRCA_DIR / "20x_512px" / "slide_features_titan"
TITAN_UCEC_DIR = TRIDENT_UCEC_DIR / "20x_512px" / "slide_features_titan"

# clam outputs — mSTAR pipeline
# 256x256 patches at 20x to match mSTAR pretraining
CLAM_MSTAR_DIR        = DATA_DIR / "clam_mstar"
BRCA_COORDS_MSTAR_DIR = CLAM_MSTAR_DIR / "cptac_brca" / "patches"
UCEC_COORDS_MSTAR_DIR = CLAM_MSTAR_DIR / "cptac_ucec" / "patches"
BRCA_MASKS_MSTAR_DIR  = CLAM_MSTAR_DIR / "cptac_brca" / "masks"
UCEC_MASKS_MSTAR_DIR  = CLAM_MSTAR_DIR / "cptac_ucec" / "masks"

# mstar patch features — one .h5 file per slide
MSTAR_FEATURES_DIR = DATA_DIR / "patch_features" / "mstar"
MSTAR_BRCA_PT_DIR  = MSTAR_FEATURES_DIR / "cptac_brca" / "pt_files"
MSTAR_UCEC_PT_DIR  = MSTAR_FEATURES_DIR / "cptac_ucec" / "pt_files"

# mstar slide embeddings — one .pt file per slide
MSTAR_EMBEDDINGS_DIR = DATA_DIR / "slide_embeddings" / "mstar"
MSTAR_BRCA_DIR       = MSTAR_EMBEDDINGS_DIR / "cptac_brca"
MSTAR_UCEC_DIR       = MSTAR_EMBEDDINGS_DIR / "cptac_ucec"

# model weights
# mSTAR weights downloaded manually from HuggingFace
# TITAN and CONCH v1.5 downloaded automatically via HuggingFace cache
# HF_HOME redirected to data disk to avoid filling system disk on Vast.ai
WEIGHTS_DIR        = Path(os.getenv("WEIGHTS_DIR", "models/ckpts"))
MSTAR_WEIGHTS_PATH = WEIGHTS_DIR / "mSTAR.pth"
HF_CACHE_DIR       = Path(os.getenv("HF_HOME", "models/hf_cache"))

# dataset csv files
# CLAM and mSTAR both require a CSV listing slide IDs and file paths
# generated automatically from downloaded slides by download_cptac.py
DATASET_CSV_DIR = Path("dataset_csv")
BRCA_CSV        = DATASET_CSV_DIR / "cptac_brca.csv"
UCEC_CSV        = DATASET_CSV_DIR / "cptac_ucec.csv"

# logs
LOGS_DIR = DATA_DIR / "logs"

# all directories
ALL_DIRS = [
    BRCA_SLIDES_DIR,
    UCEC_SLIDES_DIR,
    TRIDENT_BRCA_DIR,
    TRIDENT_UCEC_DIR,
    BRCA_COORDS_MSTAR_DIR,
    UCEC_COORDS_MSTAR_DIR,
    BRCA_MASKS_MSTAR_DIR,
    UCEC_MASKS_MSTAR_DIR,
    MSTAR_BRCA_PT_DIR,
    MSTAR_UCEC_PT_DIR,
    MSTAR_BRCA_DIR,
    MSTAR_UCEC_DIR,
    WEIGHTS_DIR,
    HF_CACHE_DIR,
    LOGS_DIR,
    DATASET_CSV_DIR,
]


def create_all_dirs() -> None:
    """Create all required directories if they don't exist."""
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


def verify_all_dirs() -> None:
    """Print status of all directories — useful to check setup on Vast.ai."""
    for d in ALL_DIRS:
        status = "o" if d.exists() else "x"
        print(f"  {status}  {d}")

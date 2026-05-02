import logging
import csv
from pathlib import Path
from typing import Iterator

import h5py
import torch
import numpy as np


# logging

def get_logger(name: str) -> logging.Logger:
    """Return a consistently formatted logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# slide discovery

def find_slides(slides_dir: Path,
                extensions: tuple = (".svs", ".tiff", ".tif", ".ndpi")) -> list[Path]:
    """Return all slide files in a directory matching known WSI extensions."""
    slides = []
    for ext in extensions:
        slides.extend(slides_dir.glob(f"*{ext}"))
    return sorted(slides)


def slide_id_from_path(slide_path: Path) -> str:
    """Extract slide ID from file path by stripping the extension."""
    return slide_path.stem


# dataset CSV generation

def generate_dataset_csv(slides_dir: Path, csv_path: Path, logger=None) -> int:
    """
    Generate a CLAM/mSTAR compatible dataset CSV from a directory of slides.

    CSV format:
        slide_id, full_path

    Returns the number of slides written.
    """
    slides = find_slides(slides_dir)
    if not slides:
        raise FileNotFoundError(f"no slides found in {slides_dir}")

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["slide_id", "full_path"])
        for slide in slides:
            writer.writerow([slide_id_from_path(slide), str(slide.resolve())])
            if logger:
                logger.info(f"  found: {slide.name} ({slide.stat().st_size / 1024 / 1024:.1f} MB)")

    return len(slides)

# loading patch features

def load_h5_features(h5_path: Path) -> tuple[torch.Tensor, torch.Tensor, int]:
    """
    Load CONCH v1.5 patch features from a CLAM .h5 file.

    Returns:
        features: (num_patches, embed_dim) tensor
        coords:   (num_patches, 2) tensor of (x, y) coordinates
        patch_size_lv0: patch size at level 0 magnification
    """
    with h5py.File(h5_path, "r") as f:
        features       = torch.from_numpy(f["features"][:])
        coords         = torch.from_numpy(f["coords"][:])
        patch_size_lv0 = int(f["coords"].attrs["patch_size_level0"])
    return features, coords, patch_size_lv0


def load_pt_features(pt_path: Path) -> torch.Tensor:
    """
    Load mSTAR patch features from a .pt file.

    Returns:
        features: (num_patches, embed_dim) tensor
    """
    return torch.load(pt_path, map_location="cpu")


# saving slide embeddings

def save_slide_embedding(embedding: torch.Tensor, slide_id: str, output_dir: Path) -> Path:
    """
    Save a single slide embedding as an .h5 file named by slide ID.

    Returns the path the embedding was saved to.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{slide_id}.h5"
    with h5py.File(output_path, "w") as f:
        f.create_dataset("features", data=embedding.cpu().numpy())
    return output_path


# iteration helpers

def iter_h5_slides(h5_dir: Path) -> Iterator[tuple[str, Path]]:
    """Yield (slide_id, h5_path) for all .h5 files in a directory."""
    for h5_path in sorted(h5_dir.glob("*.h5")):
        yield h5_path.stem, h5_path


def iter_pt_slides(pt_dir: Path) -> Iterator[tuple[str, Path]]:
    """Yield (slide_id, pt_path) for all .pt files in a directory."""
    for pt_path in sorted(pt_dir.glob("*.pt")):
        yield pt_path.stem, pt_path

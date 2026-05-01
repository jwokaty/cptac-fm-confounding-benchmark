#!/usr/bin/env bash
# clam_segment_patch_mstar.sh
# CLAM tissue segmentation + tiling for mSTAR pipeline
# patch size: 256x256 at 20x (matches mSTAR pretraining setup)

set -euo pipefail

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DATA_DIR=${DATA_DIR:-data}
CLAM_REPO=${CLAM_REPO:-clam_repo}

if [ ! -f "$CLAM_REPO/create_patches_fp.py" ]; then
    echo "ERROR: CLAM repo not found at $CLAM_REPO"
    echo "run: git clone https://github.com/mahmoodlab/CLAM.git clam_repo"
    exit 1
fi

segment_and_patch() {
    local collection=$1
    local slides_dir=$2
    local save_dir=$3

    echo "=== $collection: segmentation + tiling (256x256) ==="
    echo "  slides: $slides_dir"
    echo "  output: $save_dir"

    python "$CLAM_REPO/create_patches_fp.py" \
        --source "$slides_dir" \
        --save_dir "$save_dir" \
        --patch_size 256 \
        --step_size 256 \
        --seg \
        --patch \
        --no_auto_skip

    echo "=== $collection: done ==="
}

segment_and_patch \
    "CPTAC-BRCA" \
    "$DATA_DIR/slides/cptac_brca" \
    "$DATA_DIR/clam_mstar/cptac_brca"

segment_and_patch \
    "CPTAC-UCEC" \
    "$DATA_DIR/slides/cptac_ucec" \
    "$DATA_DIR/clam_mstar/cptac_ucec"

echo ""
echo "mSTAR tiling complete"
echo "coordinate .h5 files saved to:"
echo "  $DATA_DIR/clam_mstar/cptac_brca/patches/"
echo "  $DATA_DIR/clam_mstar/cptac_ucec/patches/"


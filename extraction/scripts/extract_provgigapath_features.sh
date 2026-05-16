#!/usr/bin/env bash
# extract_provgigapath_features.sh
# runs the full Prov-GigaPath pipeline via TRIDENT in one step:
#   1. tissue segmentation
#   2. tiling into 256x256 patches at 20x
#   3. Prov-GigaPath patch feature extraction
#   4. Prov-GigaPath slide-level pooling
# output: one .h5 slide embedding per slide in
#   trident_provgigapath/{collection}/20x_256px/slide_features_gigapath/

set -euo pipefail

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

DATA_DIR=${DATA_DIR:-data}
HF_HOME=${HF_HOME:-models/hf_cache}
GPU=${GPU:-0}

export HF_HOME
export CUDA_VISIBLE_DEVICES=$GPU

run_trident() {
    local collection=$1
    local slides_dir=$2
    local job_dir=$3

    echo "=== $collection: Prov-GigaPath pipeline via TRIDENT ==="
    echo "  slides: $slides_dir"
    echo "  output: $job_dir"

    trident batch -- \
        --task all \
        --wsi_dir "$slides_dir" \
        --job_dir "$job_dir" \
        --patch_encoder gigapath \
        --slide_encoder gigapath \
        --mag 20 \
        --patch_size 256

    echo "=== $collection: done ==="
}

run_trident \
    "CPTAC-BRCA" \
    "$DATA_DIR/slides/cptac_brca" \
    "$DATA_DIR/trident_provgigapath/cptac_brca"

run_trident \
    "CPTAC-UCEC" \
    "$DATA_DIR/slides/cptac_ucec" \
    "$DATA_DIR/trident_provgigapath/cptac_ucec"

echo ""
echo "Prov-GigaPath pipeline complete"
echo "slide embeddings saved to:"
echo "  $DATA_DIR/trident_provgigapath/cptac_brca/20x_256px/slide_features_gigapath/"
echo "  $DATA_DIR/trident_provgigapath/cptac_ucec/20x_256px/slide_features_gigapath/"

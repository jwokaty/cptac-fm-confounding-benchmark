#!/usr/bin/env bash
# extract_mstar_features.sh
# mSTAR patch feature extraction
# reads 256x256 coordinate .h5 files from clam_mstar/
# writes mSTAR patch features to patch_features/mstar/

set -euo pipefail

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

DATA_DIR=${DATA_DIR:-data}
MSTAR_REPO=${MSTAR_REPO:-mstar_repo}

if [ ! -f "$MSTAR_REPO/Feature_extract/extract_feature.py" ]; then
    echo "ERROR: mSTAR repo not found at $MSTAR_REPO"
    echo "run: git clone https://github.com/Innse/mSTAR.git mstar_repo"
    exit 1
fi

extract_features() {
    local collection=$1
    local coords_dir=$2
    local slides_dir=$3
    local features_dir=$4
    local csv_path=$5

    echo "=== $collection: mSTAR feature extraction ==="
    echo "  coords:   $coords_dir"
    echo "  slides:   $slides_dir"
    echo "  features: $features_dir"

    export CUDA_VISIBLE_DEVICES=${GPU:-0}

    uv run python "$MSTAR_REPO/Feature_extract/extract_feature.py" \
        --data_h5_dir "$coords_dir" \
        --data_slide_dir "$slides_dir" \
        --csv_path "$csv_path" \
        --feat_dir "$features_dir" \
        --batch_size 256 \
        --model mSTAR \
        --slide_ext .svs

    echo "=== $collection: done ==="
}

extract_features \
    "CPTAC-BRCA" \
    "$DATA_DIR/clam_mstar/cptac_brca/patches" \
    "$BRCA_SLIDES_DIR" \
    "$DATA_DIR/patch_features/mstar/cptac_brca" \
    "dataset_csv/cptac_brca.csv"

extract_features \
    "CPTAC-UCEC" \
    "$DATA_DIR/clam_mstar/cptac_ucec/patches" \
    "$UCEC_SLIDES_DIR" \
    "$DATA_DIR/patch_features/mstar/cptac_ucec" \
    "dataset_csv/cptac_ucec.csv"

echo ""
echo "mSTAR feature extraction complete"
echo "features saved to:"
echo "  $DATA_DIR/patch_features/mstar/cptac_brca/pt_files/"
echo "  $DATA_DIR/patch_features/mstar/cptac_ucec/pt_files/"

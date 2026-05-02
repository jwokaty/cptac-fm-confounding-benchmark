#!/usr/bin/env bash
# save_outputs.sh
# compresses and saves slide embeddings before shutting down Vast.ai instance
# run this as the last step before terminating the instance

set -euo pipefail

if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

DATA_DIR=${DATA_DIR:-data}
OUTPUTS_DIR=${OUTPUTS_DIR:-outputs}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== saving outputs ==="
echo "timestamp: $TIMESTAMP"

# create outputs directory
mkdir -p "$OUTPUTS_DIR"

# verify embeddings exist before compressing
check_dir() {
    local dir=$1
    local name=$2
    local count
    count=$(find "$dir" -name "*.h5" 2>/dev/null | wc -l)
    if [ "$count" -eq 0 ]; then
        echo "WARNING: no .h5 files found in $dir — $name may not have completed"
        return 1
    fi
    echo "  $name: $count embeddings found"
    return 0
}

echo "checking embeddings..."
check_dir "$DATA_DIR/trident/cptac_brca/20x_512px_0px_overlap/slide_features_titan" "TITAN BRCA"
check_dir "$DATA_DIR/trident/cptac_ucec/20x_512px_0px_overlap/slide_features_titan" "TITAN UCEC"
check_dir "$DATA_DIR/slide_embeddings/mstar/cptac_brca" "mSTAR BRCA"
check_dir "$DATA_DIR/slide_embeddings/mstar/cptac_ucec" "mSTAR UCEC"

# compress titan embeddings
echo "compressing TITAN embeddings..."
tar -czf "$OUTPUTS_DIR/titan_embeddings_$TIMESTAMP.tar.gz" \
    -C "$DATA_DIR/trident" \
    cptac_brca/20x_512px/slide_features_titan \
    cptac_ucec/20x_512px/slide_features_titan
echo "  saved to $OUTPUTS_DIR/titan_embeddings_$TIMESTAMP.tar.gz"

# compress mstar embeddings
echo "compressing mSTAR embeddings..."
tar -czf "$OUTPUTS_DIR/mstar_embeddings_$TIMESTAMP.tar.gz" \
    -C "$DATA_DIR/slide_embeddings" mstar/
echo "  saved to $OUTPUTS_DIR/mstar_embeddings_$TIMESTAMP.tar.gz"

# print file sizes
echo ""
echo "output file sizes:"
du -sh "$OUTPUTS_DIR"/*.tar.gz

echo ""
echo "=== done ==="
echo "next steps:"
echo "  1. download $OUTPUTS_DIR/*.tar.gz to your local machine"
echo "  2. verify contents with: tar -tzf <filename>"
echo "  3. then terminate the Vast.ai instance"

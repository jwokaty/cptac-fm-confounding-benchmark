#!/usr/bin/env bash
# save_outputs.sh
# compresses and saves slide embeddings before shutting down Vast.ai instance
# run this as the last step before terminating the instance

set -euo pipefail

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
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
    count=$(find "$dir" -name "*.h5" -o -name "*.pt" 2>/dev/null | wc -l)
    if [ "$count" -eq 0 ]; then
        echo "WARNING: no embedding files found in $dir — $name may not have completed"
        return 1
    fi
    echo "  $name: $count embeddings found"
    return 0
}

echo "checking embeddings..."
check_dir "$DATA_DIR/trident_provgigapath/cptac_brca/20x_256px/slide_features_gigapath" "Prov-GigaPath BRCA"
check_dir "$DATA_DIR/trident_provgigapath/cptac_ucec/20x_256px/slide_features_gigapath" "Prov-GigaPath UCEC"

# compress prov-gigapath embeddings
echo "compressing Prov-GigaPath embeddings..."
tar -czf "$OUTPUTS_DIR/provgigapath_embeddings_$TIMESTAMP.tar.gz" \
    -C "$DATA_DIR" trident_provgigapath/
echo "  saved to $OUTPUTS_DIR/provgigapath_embeddings_$TIMESTAMP.tar.gz"

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

#!/bin/bash
# Build the verus-parser binary

set -e

cd "$(dirname "$0")"

echo "Building verus-parser..."
cargo build --release

echo "Build complete! Binary located at: target/release/verus-parser"

# Optionally copy to parent directory for easy access
cp target/release/verus-parser ../verus-parser-bin

echo "Copied binary to: ../verus-parser-bin"


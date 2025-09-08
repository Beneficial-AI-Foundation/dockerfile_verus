#!/bin/bash

# Script to build Docker image with specific Verus revision
# Usage: ./build-revision.sh [revision_hash] [image_name]

set -e

REVISION=${1:-"33c6cec7bd19818e51d2b61f629d5d2484778bed"}
IMAGE_NAME=${2:-"verus-revision"}

echo "Building Docker image with Verus revision: $REVISION"
echo "Image name: $IMAGE_NAME"

# Validate that revision looks like a git hash (40 hex characters)
if ! echo "$REVISION" | grep -qE '^[a-f0-9]{40}$'; then
    echo "Warning: '$REVISION' doesn't look like a full git hash (40 hex characters)"
    echo "It might still work if it's a valid git reference, but full hashes are recommended"
fi

# Try to find the corresponding release for this revision
echo "Looking up release for revision $REVISION..."
RELEASE_JSON=$(curl -s https://api.github.com/repos/verus-lang/verus/releases)
RELEASE=$(echo "$RELEASE_JSON" | jq -r --arg rev "$REVISION" '.[] | select(.target_commitish == $rev) | .tag_name' | head -n1)

if [ -z "$RELEASE" ]; then
    echo "Trying to find release by commit SHA in release names..."
    SHORT_REV=$(echo "$REVISION" | cut -c1-7)
    RELEASE=$(echo "$RELEASE_JSON" | jq -r --arg short_rev "$SHORT_REV" '.[] | select(.tag_name | contains($short_rev)) | .tag_name' | head -n1)
fi

if [ -n "$RELEASE" ]; then
    echo "Found matching release: $RELEASE"
else
    echo "Warning: No release found for revision $REVISION. The build may fail."
fi

# Build the Docker image
docker build \
    --build-arg VERUS_RELEASE_TYPE="$REVISION" \
    -t "$IMAGE_NAME" \
    .

echo "Docker image '$IMAGE_NAME' built successfully with Verus revision $REVISION"
if [ -n "$RELEASE" ]; then
    echo "Using release: $RELEASE"
fi
echo ""
echo "To run verification on a project, use:"
echo "docker run --rm -v \$(pwd):/workspace $IMAGE_NAME"

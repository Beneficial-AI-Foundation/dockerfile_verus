#!/bin/bash

# Default values
WORK_DIR="/workspace"
MODULE=""
EXTRA_ARGS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --work-dir)
            WORK_DIR="$2"
            shift 2
            ;;
        --verify-only-module)
            MODULE="$2"
            shift 2
            ;;
        *)
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
    esac
done

# Change to the specified working directory
cd "$WORK_DIR" || { echo "Error: Cannot change to directory $WORK_DIR"; exit 1; }

# Build the cargo verus command
CMD="cargo verus verify"

# Add module-specific verification if specified
if [ -n "$MODULE" ]; then
    CMD="$CMD -- --verify-only-module $MODULE"
fi

# Add any extra arguments
if [ -n "$EXTRA_ARGS" ]; then
    CMD="$CMD $EXTRA_ARGS"
fi

echo "Running: $CMD"
echo "Working directory: $(pwd)"

# Execute the command
eval $CMD

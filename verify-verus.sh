#!/bin/bash

# Default values
WORK_DIR="/workspace"
MODULE=""
PACKAGE=""
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
        --package|-p)
            PACKAGE="$2"
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

# Check if we're in a workspace member directory
if [ -f "Cargo.toml" ] && [ -f "../Cargo.toml" ]; then
    # Check if parent is a workspace
    if grep -q "\[workspace\]" ../Cargo.toml 2>/dev/null; then
        echo "Detected workspace member directory"
        # Ensure we have access to workspace dependencies
        export CARGO_TARGET_DIR="${CARGO_TARGET_DIR:-../target}"
    fi
fi

# Build the cargo verus command
CMD="cargo verus verify"

# Add package selection if specified (for workspace projects)
if [ -n "$PACKAGE" ]; then
    CMD="$CMD -p $PACKAGE"
fi

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
echo "Verus version: $(/root/.cargo/bin/verus-x86-linux/verus --version)"

# Debug information
echo "------- Debug Information -------"
echo "Contents of working directory:"
ls -la
echo "Checking for Cargo.toml:"
if [ -f "Cargo.toml" ]; then
    echo "Cargo.toml found in $(pwd)"
    echo "Package name: $(grep '^name' Cargo.toml | head -1)"
fi

# Check the module structure
if [ -n "$MODULE" ]; then
    echo "Looking for module: $MODULE"
    # Try to find the corresponding file
    MODULE_PATH=$(echo "$MODULE" | sed 's/::/\//g')
    echo "Expected file path pattern: src/${MODULE_PATH}.rs or src/${MODULE_PATH}/mod.rs"
    find src -name "*.rs" | grep -E "(${MODULE_PATH}\.rs|${MODULE_PATH}/mod\.rs)" || echo "Module file not found with simple search"
fi

echo "------- End Debug Information -------"

# Check if we have a Cargo.lock file - sometimes needed for workspaces
if [ ! -f "Cargo.lock" ] && [ -f "../Cargo.lock" ]; then
    echo "Copying Cargo.lock from parent directory..."
    cp ../Cargo.lock .
fi

# Execute the command
echo "Executing: $CMD"
eval $CMD

#!/bin/bash

# Default values
WORK_DIR="/workspace"
MODULE=""
FUNCTION=""
PACKAGE=""
EXTRA_ARGS=""
JSON_OUTPUT=""

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
        --verify-function)
            FUNCTION="$2"
            shift 2
            ;;
        --package|-p)
            PACKAGE="$2"
            shift 2
            ;;
        --json-output)
            JSON_OUTPUT="$2"
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

# Build the verus-specific arguments
VERUS_ARGS=""

# Add module-specific verification if specified
if [ -n "$MODULE" ]; then
    VERUS_ARGS="$VERUS_ARGS --verify-only-module $MODULE"
fi

# Add function-specific verification if specified
if [ -n "$FUNCTION" ]; then
    VERUS_ARGS="$VERUS_ARGS --verify-function $FUNCTION"
fi

# Add verus arguments if any were specified
if [ -n "$VERUS_ARGS" ]; then
    CMD="$CMD --$VERUS_ARGS"
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

# Show function verification info
if [ -n "$FUNCTION" ]; then
    echo "Verifying function: $FUNCTION"
    if [ -n "$MODULE" ]; then
        echo "In module: $MODULE"
    fi
fi

echo "------- End Debug Information -------"

# Check if we have a Cargo.lock file - sometimes needed for workspaces
if [ ! -f "Cargo.lock" ] && [ -f "../Cargo.lock" ]; then
    echo "Copying Cargo.lock from parent directory..."
    cp ../Cargo.lock .
fi

# Build the project first to ensure all dependencies and modules are resolved
#echo "Building project to ensure module resolution..."
#BUILD_CMD="cargo build"
#if [ -n "$PACKAGE" ]; then
#    BUILD_CMD="$BUILD_CMD -p $PACKAGE"
#fi
#echo "Running: $BUILD_CMD"
#eval $BUILD_CMD

# Create output directory if JSON output is specified
if [ -n "$JSON_OUTPUT" ]; then
    mkdir -p "$(dirname "$JSON_OUTPUT")"
fi

# Create temporary file for output
TEMP_OUTPUT=$(mktemp /tmp/verus_output.XXXXXX)

# Execute the command and capture both stdout and stderr
echo "Executing: $CMD"
echo "Capturing output to: $TEMP_OUTPUT"

# Run the command and capture output, preserving exit code
set +e
eval "$CMD" 2>&1 | tee "$TEMP_OUTPUT"
VERUS_EXIT_CODE=${PIPESTATUS[0]}
set -e

echo ""
echo "Verus command completed with exit code: $VERUS_EXIT_CODE"

# Process output if JSON output is requested
if [ -n "$JSON_OUTPUT" ]; then
    echo "Processing output and generating JSON report..."
    
    # Use Python script to analyze output and create JSON report
    python3 /usr/local/bin/find_verus_functions.py \
        "$WORK_DIR" \
        --output-file "$TEMP_OUTPUT" \
        --json-output "$JSON_OUTPUT" \
        --format json \
        --exit-code "$VERUS_EXIT_CODE"
    
    if [ $? -eq 0 ]; then
        echo "JSON report generated: $JSON_OUTPUT"
        
        # Show summary from JSON if possible
        if command -v jq >/dev/null 2>&1; then
            echo ""
            echo "=== VERIFICATION SUMMARY ==="
            jq -r '.summary | "Total functions: \(.total_functions)", "Verified: \(.verified_functions)", "Failed: \(.failed_functions)", "Compilation errors: \(.compilation_errors)", "Warnings: \(.compilation_warnings)"' "$JSON_OUTPUT"
            echo "Status: $(jq -r '.status' "$JSON_OUTPUT")"
        else
            echo "Install 'jq' to see JSON summary in terminal"
        fi
    else
        echo "Warning: Failed to generate JSON report"
    fi
else
    echo "No JSON output requested. Use --json-output <file> to generate detailed report."
fi

# Clean up temporary file
rm -f "$TEMP_OUTPUT"

# Exit with the same code as the Verus command
exit $VERUS_EXIT_CODE

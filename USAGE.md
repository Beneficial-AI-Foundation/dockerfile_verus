# Verus Verification Tool Usage Guide

## Overview

The enhanced `find_verus_functions.py` is now a complete verification tool that can:
1. **Run** Verus verification
2. **Analyze** verification results
3. **Generate** detailed JSON reports

## NEW: Verus Parser with verus_syn

We now provide an accurate Rust-based parser using `verus_syn` instead of adhoc regex parsing. This provides more accurate function extraction with proper AST parsing.

### Building the Parser

```bash
cd verus-parser
./build.sh
```

This builds a Rust binary that can be called from Python or used directly from the command line.

### Using the verus_syn Parser

#### Option 1: Drop-in Replacement Script

Use `find_verus_functions_syn.py` instead of `find_verus_functions.py`:

```bash
# Extract all functions
./find_verus_functions_syn.py /path/to/project --json-output report.json

# Run verification and analyze
./find_verus_functions_syn.py /path/to/project --run-verification --json-output report.json

# Exclude Verus constructs (spec, proof, exec)
./find_verus_functions_syn.py /path/to/project --exclude-verus-constructs --json-output report.json
```

#### Option 2: Python Wrapper

```python
from verus_parser_wrapper import VerusParser

parser = VerusParser()

# Get all functions with line numbers
functions_by_file = parser.find_all_functions("/path/to/project")

# Get just function names
function_names = parser.get_function_list("/path/to/project")

# Get full information
data = parser.parse_functions("/path/to/project", 
                              include_verus_constructs=True,
                              show_kind=True,
                              show_visibility=True)
```

#### Option 3: Direct Binary Usage

```bash
# JSON output
./verus-parser-bin /path/to/project --format json > output.json

# Text output (just function names)
./verus-parser-bin /path/to/project --format text

# Detailed output
./verus-parser-bin /path/to/project --format detailed --show-kind --show-visibility
```

See `verus-parser/README.md` for more details.

### Advantages of verus_syn Parser

- **Accurate**: Uses proper AST parsing instead of regex
- **Handles edge cases**: Complex nested structures, macros, etc.
- **Precise line numbers**: Start and end lines for each function
- **Verus-aware**: Understands Verus-specific constructs
- **Maintainable**: Leverages well-tested `verus_syn` library

## Usage Modes

### 1. Run Verification + Generate Report (Recommended for Local Development)

Run verification and immediately get a JSON report:

```bash
python3 find_verus_functions.py ../curve25519-dalek \
  --run-verification \
  --json-output report.json
```

**With module filtering:**
```bash
python3 find_verus_functions.py ../curve25519-dalek \
  --run-verification \
  --verify-only-module backend::serial::u64::field_verus \
  --json-output report.json
```

**With function filtering:**
```bash
python3 find_verus_functions.py ../curve25519-dalek \
  --run-verification \
  --verify-function pow2k \
  --json-output report.json
```

**For workspace projects:**
```bash
python3 find_verus_functions.py ../my-workspace \
  --run-verification \
  --package my-crate \
  --json-output report.json
```

### 2. Analyze Existing Verification Output

If you already have verification output from a previous run:

```bash
python3 find_verus_functions.py ../curve25519-dalek \
  --output-file verus_output.txt \
  --json-output report.json
```

### 3. Docker Usage (Original Workflow)

For Docker environments, use the original `verify-verus.sh` script:

```bash
# Inside Docker container
./verify-verus.sh \
  --work-dir /workspace/project \
  --json-output report.json
```

## JSON Report Structure

The generated JSON report contains:

```json
{
  "status": "verification_failed | success | compilation_failed",
  "summary": {
    "total_functions": 814,
    "verified_functions": 812,
    "failed_functions": 2,
    "compilation_errors": 0,
    "compilation_warnings": 29,
    "verification_errors": 1
  },
  "compilation": {
    "errors": [...],
    "warnings": [...]
  },
  "verification": {
    "verified_functions": [...],
    "failed_functions": ["func1", "func2"],
    "errors": [
      {
        "error_type": "assertion failed",
        "file": "path/to/file.rs",
        "line": 1340,
        "column": 24,
        "message": "error: assertion failed",
        "full_error_text": "..."
      }
    ]
  },
  "functions_by_file": {
    "file.rs": [
      {"name": "function_name", "line": 123}
    ]
  }
}
```

## Quick Examples

### Local Development Workflow

```bash
# Quick verification of entire project
python3 find_verus_functions.py ../curve25519-dalek --run-verification --json-output report.json

# Check a specific module while developing
python3 find_verus_functions.py ../curve25519-dalek \
  --run-verification \
  --verify-only-module backend::serial::u64::field \
  --json-output module_report.json

# Debug a specific function
python3 find_verus_functions.py ../curve25519-dalek \
  --run-verification \
  --verify-function lemma_cast_then_mod_51 \
  --json-output function_report.json
```

### View Summary with jq

```bash
# View summary
jq '.summary' report.json

# List failed functions
jq '.verification.failed_functions' report.json

# View detailed errors
jq '.verification.errors' report.json

# Show compilation warnings
jq '.compilation.warnings' report.json
```

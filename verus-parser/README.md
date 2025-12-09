# Verus Parser

A Rust-based parser using `verus_syn` for accurately extracting function information from Verus/Rust code.

This replaces the adhoc regex-based parsing in `find_verus_functions.py` with proper AST parsing.

## Features

- **Accurate parsing** using `verus_syn` (Verus-specific fork of `syn`)
- **Handles Verus macros** like `verus!{}` and `cfg_if!{}`
- **Supports all function types**:
  - Regular functions (`fn`)
  - Verus-specific functions (`spec fn`, `proof fn`, `exec fn`)
  - Const functions (`const fn`)
  - Trait methods
  - Impl methods
- **Precise line numbers** for function start and end
- **Multiple output formats**: JSON, text, detailed
- **Visibility tracking**: public vs private functions
- **Function classification**: standalone, trait, impl

## Building

### Prerequisites

- Rust toolchain (1.70+)
- Cargo

### Build Instructions

```bash
cd verus-parser
./build.sh
```

This will:
1. Build the Rust binary in release mode
2. Copy the binary to `../verus-parser-bin` for easy access

Alternatively, build manually:

```bash
cargo build --release
# Binary will be at target/release/verus-parser
```

## Usage

### Direct Usage (Command Line)

```bash
# Parse a directory and output JSON
./verus-parser /path/to/rust/project --format json

# Parse a single file
./verus-parser /path/to/file.rs --format json

# Get just function names (text format)
./verus-parser /path/to/project --format text

# Get detailed output with line numbers
./verus-parser /path/to/project --format detailed

# Exclude Verus-specific constructs (spec, proof, exec)
./verus-parser /path/to/project --format json --include-verus-constructs false

# Show function visibility and kind
./verus-parser /path/to/project --format detailed --show-visibility --show-kind
```

### Python Wrapper

The Python wrapper (`verus_parser_wrapper.py`) provides a convenient interface:

```python
from verus_parser_wrapper import VerusParser

# Initialize the parser
parser = VerusParser()

# Parse functions and get full information
data = parser.parse_functions("/path/to/project")
print(f"Found {data['summary']['total_functions']} functions")

# Get function names with line numbers (compatible with old API)
functions_by_file = parser.find_all_functions("/path/to/project")
for file_path, functions in functions_by_file.items():
    for func_name, line_number in functions:
        print(f"{func_name} @ {file_path}:{line_number}")

# Get just function names
function_names = parser.get_function_list("/path/to/project")
```

### Drop-in Replacement

`find_verus_functions_syn.py` is a drop-in replacement for `find_verus_functions.py`:

```bash
# Same interface as the old script
./find_verus_functions_syn.py /path/to/project --json-output report.json

# Run verification and analyze
./find_verus_functions_syn.py /path/to/project --run-verification --json-output report.json

# Exclude Verus constructs
./find_verus_functions_syn.py /path/to/project --exclude-verus-constructs --json-output report.json
```

## Output Format

### JSON Format

```json
{
  "functions": [
    {
      "name": "my_function",
      "file": "/path/to/file.rs",
      "start_line": 10,
      "end_line": 25,
      "kind": "fn",
      "visibility": "pub",
      "context": "standalone"
    }
  ],
  "functions_by_file": {
    "/path/to/file.rs": [
      {
        "name": "my_function",
        "start_line": 10,
        "end_line": 25
      }
    ]
  },
  "summary": {
    "total_functions": 1,
    "total_files": 1
  }
}
```

### Text Format

Simple list of function names, one per line:

```
add
multiply
spec_lemma
proof_helper
```

### Detailed Format

Human-readable format with full information:

```
my_function [fn] (pub) @ /path/to/file.rs:10:25 in standalone
helper_function [spec fn] (private) @ /path/to/file.rs:30:45 in impl
```

## Architecture

- **Rust binary** (`verus-parser`): Uses `verus_syn` for AST parsing
- **Python wrapper** (`verus_parser_wrapper.py`): Subprocess interface to Rust binary
- **Drop-in replacement** (`find_verus_functions_syn.py`): Compatible with existing scripts

## Advantages over Regex-based Parsing

1. **Accurate**: Uses proper AST parsing instead of regex
2. **Handles edge cases**: Complex nested structures, macros, etc.
3. **Line numbers**: Precise start and end line numbers
4. **Verus-aware**: Understands Verus-specific constructs
5. **Maintainable**: Leverages well-tested `verus_syn` library

## Dependencies

The Rust binary depends on:
- `verus_syn`: Verus-specific fork of `syn` for parsing
- `serde`/`serde_json`: JSON serialization
- `clap`: Command-line argument parsing
- `walkdir`: Directory traversal

## Testing

Test the parser on a simple file:

```bash
# Create a test file
cat > test.rs << 'EOF'
verus! {
    spec fn my_spec(x: int) -> int {
        x + 1
    }
    
    proof fn my_proof() {
        assert(true);
    }
    
    fn my_regular_function() -> i32 {
        42
    }
}
EOF

# Parse it
./verus-parser test.rs --format detailed --show-kind
```

Expected output:
```
my_spec [spec fn] @ test.rs:2:4 in standalone
my_proof [proof fn] @ test.rs:6:8 in standalone
my_regular_function [fn] @ test.rs:10:12 in standalone

Summary: 3 functions in 1 files
```

## Troubleshooting

### Binary not found

If you get "verus-parser binary not found":
1. Make sure you've built the binary: `cd verus-parser && cargo build --release`
2. Check the binary exists: `ls verus-parser/target/release/verus-parser`
3. Or specify the path explicitly when using Python wrapper

### Parse errors

If you get parse errors on valid Rust code:
- Make sure the Rust code compiles
- Check that you're using a compatible `verus_syn` version
- File an issue if the problem persists

## License

Same as the parent project.


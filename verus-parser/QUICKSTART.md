# Quick Start Guide

Get up and running with the verus_syn parser in 5 minutes.

## Step 1: Build the Parser (One-time)

```bash
cd verus-parser
./build.sh
```

**Expected output:**
```
Building verus-parser...
   Compiling verus_syn v0.0.0-2025-11-16-0050
   Compiling verus-parser v0.1.0
    Finished release [optimized] target(s) in 45.2s
Build complete! Binary located at: target/release/verus-parser
Copied binary to: ../verus-parser-bin
```

**Troubleshooting:**
- If Rust is not installed: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- If build fails: Check Rust version with `rustc --version` (need 1.70+)

## Step 2: Test the Parser

```bash
# Test on a simple file
echo 'verus! { fn test() {} }' > test.rs
./target/release/verus-parser test.rs --format text
# Expected: test

# Test on a directory
./target/release/verus-parser ../3192/curve25519-dalek/src --format json | head -20
```

## Step 3: Use from Python

```python
from verus_parser_wrapper import VerusParser

parser = VerusParser()
functions = parser.get_function_list("../3192/curve25519-dalek/src")
print(f"Found {len(functions)} functions")
print("First 5:", functions[:5])
```

## Step 4: Use as Drop-in Replacement

```bash
# Instead of:
# ./find_verus_functions.py /path/to/project --json-output report.json

# Use:
./find_verus_functions_syn.py /path/to/project --json-output report.json
```

## Common Use Cases

### Extract All Functions

```bash
./verus-parser-bin /path/to/project --format text > functions.txt
```

### Get Detailed Information

```bash
./verus-parser-bin /path/to/project --format detailed --show-kind --show-visibility
```

### Generate JSON Report

```bash
./verus-parser-bin /path/to/project --format json > report.json
```

### Exclude Verus Constructs

```bash
./verus-parser-bin /path/to/project --format text --include-verus-constructs false
```

### Python Integration

```python
from verus_parser_wrapper import VerusParser

parser = VerusParser()

# Get functions by file
functions_by_file = parser.find_all_functions("/path/to/project")
for file_path, functions in functions_by_file.items():
    print(f"\n{file_path}:")
    for func_name, line_num in functions:
        print(f"  {func_name} @ line {line_num}")

# Get detailed information
data = parser.parse_functions(
    "/path/to/project",
    include_verus_constructs=True,
    show_kind=True,
    show_visibility=True
)

for func in data["functions"]:
    print(f"{func['visibility']} {func['kind']} {func['name']}")
    print(f"  {func['file']}:{func['start_line']}-{func['end_line']}")
```

## Next Steps

- Read `README.md` for detailed documentation
- See `MIGRATION_GUIDE.md` for migration from regex parser
- Check `COMPARISON.md` for feature comparison
- Run `./test_parser.sh` for comprehensive tests

## Help

```bash
# Command-line help
./verus-parser-bin --help

# Python help
python3 -c "from verus_parser_wrapper import VerusParser; help(VerusParser)"

# Drop-in replacement help
./find_verus_functions_syn.py --help
```

## Troubleshooting

### "Binary not found"

```bash
cd verus-parser
cargo build --release
cp target/release/verus-parser ../verus-parser-bin
```

### "Parse error"

- Make sure the Rust code compiles: `cargo check`
- Check for syntax errors in the source files
- Try parsing a single file to isolate the issue

### "Import error" (Python)

```bash
# Make sure you're in the right directory
cd /path/to/dockerfile_verus
python3 -c "from verus_parser_wrapper import VerusParser; print('OK')"
```

## Performance Tips

- Use `--format text` for fastest output
- Parse specific files instead of entire directories when possible
- The binary is optimized with LTO and high optimization level

## That's It!

You're now ready to use the verus_syn parser. Enjoy more accurate function extraction! 🎉


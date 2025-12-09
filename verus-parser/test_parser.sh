#!/bin/bash
# Test script for verus-parser

set -e

echo "=== Testing Verus Parser ==="
echo

# Create a test directory
TEST_DIR=$(mktemp -d)
echo "Created test directory: $TEST_DIR"

# Create test files
cat > "$TEST_DIR/test.rs" << 'EOF'
verus! {
    spec fn my_spec(x: int) -> int {
        x + 1
    }
    
    proof fn my_proof() {
        assert(true);
    }
    
    exec fn my_exec() -> i32 {
        42
    }
    
    fn my_regular_function(a: i32, b: i32) -> i32 {
        a + b
    }
}

fn outside_verus() {
    println!("This is outside verus macro");
}

pub fn public_function() -> String {
    String::from("public")
}
EOF

cat > "$TEST_DIR/impl_test.rs" << 'EOF'
verus! {
    struct MyStruct {
        value: i32,
    }
    
    impl MyStruct {
        fn new(value: i32) -> Self {
            MyStruct { value }
        }
        
        spec fn get_value(&self) -> int {
            self.value as int
        }
    }
    
    trait MyTrait {
        fn trait_method(&self) -> i32;
        
        spec fn trait_spec(&self) -> int;
    }
}
EOF

echo "Created test files"
echo

# Build the parser if not already built
if [ ! -f "target/release/verus-parser" ]; then
    echo "Building verus-parser..."
    cargo build --release
    echo
fi

PARSER="./target/release/verus-parser"

echo "=== Test 1: Parse single file (JSON format) ==="
$PARSER "$TEST_DIR/test.rs" --format json | jq '.summary'
echo

echo "=== Test 2: Parse single file (text format) ==="
$PARSER "$TEST_DIR/test.rs" --format text
echo

echo "=== Test 3: Parse single file (detailed format with visibility and kind) ==="
$PARSER "$TEST_DIR/test.rs" --format detailed --show-visibility --show-kind
echo

echo "=== Test 4: Parse directory ==="
$PARSER "$TEST_DIR" --format json | jq '.summary'
echo

echo "=== Test 5: Exclude Verus constructs ==="
echo "With Verus constructs:"
$PARSER "$TEST_DIR/test.rs" --format text --include-verus-constructs true | wc -l
echo "functions found"
echo
echo "Without Verus constructs:"
$PARSER "$TEST_DIR/test.rs" --format text --include-verus-constructs false | wc -l
echo "functions found"
echo

echo "=== Test 6: Parse impl methods ==="
$PARSER "$TEST_DIR/impl_test.rs" --format detailed --show-kind
echo

echo "=== Test 7: Exclude methods ==="
echo "With methods:"
$PARSER "$TEST_DIR/impl_test.rs" --format text --include-methods true | wc -l
echo "functions found"
echo
echo "Without methods:"
$PARSER "$TEST_DIR/impl_test.rs" --format text --include-methods false | wc -l
echo "functions found"
echo

# Test Python wrapper if available
if command -v python3 &> /dev/null; then
    echo "=== Test 8: Python wrapper ==="
    
    cat > "$TEST_DIR/test_wrapper.py" << 'PYEOF'
import sys
sys.path.insert(0, '..')
from verus_parser_wrapper import VerusParser

parser = VerusParser(binary_path='./target/release/verus-parser')

# Test basic parsing
data = parser.parse_functions(sys.argv[1])
print(f"Found {data['summary']['total_functions']} functions in {data['summary']['total_files']} files")

# Test function list
names = parser.get_function_list(sys.argv[1])
print(f"Function names: {', '.join(names)}")
PYEOF

    python3 "$TEST_DIR/test_wrapper.py" "$TEST_DIR"
    echo
fi

# Cleanup
echo "Cleaning up test directory..."
rm -rf "$TEST_DIR"

echo
echo "=== All tests passed! ==="


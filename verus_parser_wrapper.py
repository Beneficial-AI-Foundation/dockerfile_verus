#!/usr/bin/env python3
"""
Wrapper for the Rust-based verus-parser that uses verus_syn.
This provides a Python interface to the more accurate parsing logic.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class VerusParser:
    """Wrapper for the Rust verus-parser binary."""
    
    def __init__(self, binary_path: Optional[str] = None):
        """
        Initialize the parser wrapper.
        
        Args:
            binary_path: Path to the verus-parser binary. If None, searches in common locations.
        """
        if binary_path is None:
            # Try to find the binary in common locations
            possible_paths = [
                Path(__file__).parent / "verus-parser-bin",
                Path(__file__).parent / "verus-parser" / "target" / "release" / "verus-parser",
                Path(__file__).parent / "verus-parser" / "target" / "debug" / "verus-parser",
            ]
            
            for path in possible_paths:
                if path.exists():
                    binary_path = str(path)
                    break
            else:
                raise FileNotFoundError(
                    "verus-parser binary not found. Please build it first using:\n"
                    "  cd verus-parser && cargo build --release"
                )
        
        self.binary_path = Path(binary_path)
        if not self.binary_path.exists():
            raise FileNotFoundError(f"verus-parser binary not found at: {self.binary_path}")
    
    def parse_functions(
        self, 
        path: str, 
        include_verus_constructs: bool = True,
        include_methods: bool = True,
        show_visibility: bool = False,
        show_kind: bool = False
    ) -> Dict:
        """
        Parse functions from the given path using verus_syn.
        
        Args:
            path: File or directory path to parse
            include_verus_constructs: Include spec, proof, exec functions
            include_methods: Include trait and impl methods
            show_visibility: Include visibility information (pub/private)
            show_kind: Include function kind (fn, spec fn, proof fn, etc.)
            
        Returns:
            Dictionary with parsed function information
        """
        cmd = [str(self.binary_path), path, "--format", "json"]
        
        if include_verus_constructs:
            cmd.append("--include-verus-constructs")
        
        if include_methods:
            cmd.append("--include-methods")
        
        if show_visibility:
            cmd.append("--show-visibility")
        
        if show_kind:
            cmd.append("--show-kind")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"verus-parser failed: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse verus-parser output: {e}")
    
    def find_all_functions(self, path: str, include_verus_constructs: bool = True) -> Dict[str, List[Tuple[str, int]]]:
        """
        Find all functions with their line numbers (compatible with original API).
        
        Args:
            path: File or directory path to parse
            include_verus_constructs: Include spec, proof, exec functions
            
        Returns:
            Dictionary mapping file paths to list of (function_name, line_number) tuples
        """
        data = self.parse_functions(path, include_verus_constructs=include_verus_constructs)
        
        result = {}
        for file_path, functions in data["functions_by_file"].items():
            result[file_path] = [(func["name"], func["start_line"]) for func in functions]
        
        return result
    
    def get_function_list(self, path: str, include_verus_constructs: bool = True) -> List[str]:
        """
        Get a simple list of function names.
        
        Args:
            path: File or directory path to parse
            include_verus_constructs: Include spec, proof, exec functions
            
        Returns:
            Sorted list of unique function names
        """
        data = self.parse_functions(path, include_verus_constructs=include_verus_constructs)
        names = {func["name"] for func in data["functions"]}
        return sorted(names)


def main():
    """Command-line interface for the parser wrapper."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Python wrapper for verus-parser"
    )
    parser.add_argument("path", help="Path to search (file or directory)")
    parser.add_argument("--binary-path", help="Path to verus-parser binary")
    parser.add_argument(
        "--exclude-verus-constructs", 
        action="store_true",
        help="Exclude Verus constructs (spec, proof, exec)"
    )
    parser.add_argument(
        "--exclude-methods",
        action="store_true",
        help="Exclude trait and impl methods"
    )
    parser.add_argument(
        "--show-visibility",
        action="store_true",
        help="Show function visibility"
    )
    parser.add_argument(
        "--show-kind",
        action="store_true",
        help="Show function kind"
    )
    parser.add_argument(
        "--format",
        choices=["json", "text", "names"],
        default="json",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    try:
        verus_parser = VerusParser(binary_path=args.binary_path)
        
        if args.format == "names":
            # Just print function names
            names = verus_parser.get_function_list(
                args.path,
                include_verus_constructs=not args.exclude_verus_constructs
            )
            for name in names:
                print(name)
        else:
            # Full parse
            data = verus_parser.parse_functions(
                args.path,
                include_verus_constructs=not args.exclude_verus_constructs,
                include_methods=not args.exclude_methods,
                show_visibility=args.show_visibility,
                show_kind=args.show_kind
            )
            
            if args.format == "json":
                print(json.dumps(data, indent=2))
            else:  # text
                for func in data["functions"]:
                    print(f"{func['name']} @ {func['file']}:{func['start_line']}")
    
    except Exception as e:
        print(f"Error: {e}", file=__import__("sys").stderr)
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())


#!/usr/bin/env python3
"""
Python script to find all regular Rust function names inside Verus macros.
Returns a simple list of function names without Verus-specific constructs.
Can also categorize functions based on verification results.
"""

import re
import json
from pathlib import Path


class CompilationErrorParser:
    def __init__(self):
        # Pattern to match compilation errors - improved for Cargo output
        self.error_pattern = re.compile(r'error(?:\[E\d+\])?: (.+)')
        self.cargo_error_pattern = re.compile(r'error: could not compile `([^`]+)`')
        self.warning_pattern = re.compile(r'warning: (.+)')
        self.file_location_pattern = re.compile(r'-->\s+([^:]+):(\d+):(\d+)')
        self.process_error_pattern = re.compile(r"process didn't exit successfully: (.+)")
        self.memory_error_pattern = re.compile(r'memory allocation of \d+ bytes failed')
        
    def parse_compilation_output(self, output_content):
        """Parse compilation output and extract errors and warnings."""
        errors = []
        warnings = []
        current_error = None
        current_warning = None
        
        lines = output_content.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Check for cargo compilation errors
            cargo_error_match = self.cargo_error_pattern.search(line)
            if cargo_error_match:
                if current_error:
                    errors.append(current_error)
                current_error = {
                    "message": f"Compilation failed for crate: {cargo_error_match.group(1)}",
                    "file": None,
                    "line": None,
                    "column": None,
                    "full_message": [line]
                }
                continue
                
            # Check for memory allocation errors
            if self.memory_error_pattern.search(line):
                if current_error:
                    current_error["full_message"].append(line)
                    current_error["message"] += f" - {line}"
                else:
                    errors.append({
                        "message": line,
                        "file": None,
                        "line": None,
                        "column": None,
                        "full_message": [line]
                    })
                continue
                
            # Check for process failure errors
            process_error_match = self.process_error_pattern.search(line)
            if process_error_match:
                if current_error:
                    current_error["full_message"].append(line)
                else:
                    current_error = {
                        "message": "Process execution failed",
                        "file": None,
                        "line": None,
                        "column": None,
                        "full_message": [line]
                    }
                continue
            
            # Check for standard error format
            error_match = self.error_pattern.search(line)
            if error_match:
                if current_error:
                    errors.append(current_error)
                current_error = {
                    "message": error_match.group(1).strip(),
                    "file": None,
                    "line": None,
                    "column": None,
                    "full_message": [line]
                }
                continue
                
            # Check for warning
            warning_match = self.warning_pattern.search(line)
            if warning_match:
                if current_warning:
                    warnings.append(current_warning)
                current_warning = {
                    "message": warning_match.group(1).strip(),
                    "file": None,
                    "line": None,
                    "column": None,
                    "full_message": [line]
                }
                continue
                
            # Check for file location
            location_match = self.file_location_pattern.search(line)
            if location_match:
                file_path = location_match.group(1)
                line_num = int(location_match.group(2))
                column = int(location_match.group(3))
                
                if current_error:
                    current_error["file"] = file_path
                    current_error["line"] = line_num
                    current_error["column"] = column
                    current_error["full_message"].append(line)
                elif current_warning:
                    current_warning["file"] = file_path
                    current_warning["line"] = line_num
                    current_warning["column"] = column
                    current_warning["full_message"].append(line)
                continue
                
            # Add continuation lines to current error/warning
            if current_error and (line.startswith('|') or line.startswith('^') or line.startswith('=') or 
                                line.startswith('Caused by:') or line.startswith('(signal:')):
                current_error["full_message"].append(line)
                # Update message with additional context
                if line.startswith('Caused by:'):
                    current_error["message"] += f" - {line}"
                elif '(signal:' in line:
                    current_error["message"] += f" - {line}"
            elif current_warning and (line.startswith('|') or line.startswith('^') or line.startswith('=')):
                current_warning["full_message"].append(line)
            elif line == "":
                # Empty line might end current error/warning context
                if current_error and len(current_error["full_message"]) > 0:
                    errors.append(current_error)
                    current_error = None
                if current_warning and len(current_warning["full_message"]) > 0:
                    warnings.append(current_warning)
                    current_warning = None
        
        # Don't forget the last error/warning
        if current_error:
            errors.append(current_error)
        if current_warning:
            warnings.append(current_warning)
            
        return errors, warnings


class VerificationParser:
    def __init__(self):
        # Pattern to match error lines with file path and line number
        # Example: "   --> curve25519-dalek/src/backend/serial/u64/field_verus.rs:446:20"
        self.error_pattern = re.compile(r'-->\s+([^:]+):(\d+):\d+')
    
    def parse_verification_output(self, output_file_path):
        """Parse verification output and extract files with errors and their line numbers."""
        try:
            with open(output_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (FileNotFoundError, UnicodeDecodeError, PermissionError):
            return {}
        
        errors_by_file = {}
        
        for line in content.split('\n'):
            match = self.error_pattern.search(line)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2))
                
                if file_path not in errors_by_file:
                    errors_by_file[file_path] = []
                errors_by_file[file_path].append(line_number)
        
        return errors_by_file
    
    def find_function_at_line(self, file_path, line_number, all_functions_with_lines):
        """Find the function that contains or is closest above the given line number."""
        # Try to find a matching file path (handle relative paths)
        matching_file = None
        for file_key in all_functions_with_lines.keys():
            if file_path in file_key or file_key in file_path:
                matching_file = file_key
                break
            # Also try just the filename
            if Path(file_path).name == Path(file_key).name:
                matching_file = file_key
                break
        
        if matching_file is None:
            return None
        
        functions_in_file = all_functions_with_lines[matching_file]
        closest_function = None
        closest_line = 0
        
        for func_name, func_line in functions_in_file:
            if func_line <= line_number and func_line > closest_line:
                closest_function = func_name
                closest_line = func_line
        
        return closest_function


class RustFunctionFinder:
    def __init__(self):
        # Pattern to match the start of a verus macro block
        self.verus_start_pattern = re.compile(r'\bverus!\s*\{')
        
        # Pattern to match only regular function definitions (not spec, proof, exec)
        # This pattern ensures we don't match verus keywords before 'fn'
        # We need to handle cases like "pub proof fn", "pub open spec fn", etc.
        self.function_pattern = re.compile(r'(?:pub\s+)?(?!(?:spec|proof|exec|open|uninterp)\s+(?:spec\s+)?fn\s)fn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
        
        # Pattern to match const functions as well (but not spec const fn)
        self.const_fn_pattern = re.compile(r'(?:pub\s+)?(?!(?:spec|open|uninterp)\s+)const\s+fn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')

    def find_matching_brace(self, content, start_pos):
        """Find the position of the matching closing brace for a verus! macro."""
        brace_count = 0
        i = start_pos
        
        while i < len(content):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return i
            elif content[i] == '"':
                # Skip string literals
                i += 1
                while i < len(content) and content[i] != '"':
                    if content[i] == '\\':
                        i += 1  # Skip escaped character
                    i += 1
            elif content[i:i+2] == '/*':
                # Skip block comments
                i += 2
                while i < len(content) - 1 and content[i:i+2] != '*/':
                    i += 1
                i += 1  # Skip the '*/'
            elif content[i:i+2] == '//':
                # Skip line comments
                while i < len(content) and content[i] != '\n':
                    i += 1
            i += 1
        
        return -1  # No matching brace found

    def extract_verus_blocks(self, content):
        """Extract all verus! macro blocks from the content with their line numbers."""
        blocks = []
        start = 0
        
        while True:
            match = self.verus_start_pattern.search(content, start)
            if not match:
                break
                
            # Find the opening brace
            brace_start = match.end() - 1  # The '{' character
            
            # Find the matching closing brace
            brace_end = self.find_matching_brace(content, brace_start)
            if brace_end == -1:
                break  # Malformed block
                
            # Extract the block content
            block_content = content[match.start():brace_end + 1]
            # Calculate line number where the block starts
            block_start_line = content[:match.start()].count('\n') + 1
            blocks.append((block_content, block_start_line))
            
            start = brace_end + 1
            
        return blocks

    def extract_functions_from_block(self, block_content, block_start_line=0):
        """Extract function names and their line numbers from a Verus block."""
        functions = []
        
        # Remove comments to avoid false matches
        content_no_comments = self.remove_comments(block_content)
        
        # Find all function-like patterns
        # Pattern to match any function definition with capture groups for keywords and name
        all_fn_pattern = re.compile(r'(?:pub\s+)?((?:spec|proof|exec|open|uninterp|const)\s+)*fn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
        
        matches = all_fn_pattern.finditer(content_no_comments)
        for match in matches:
            keywords = match.group(1) if match.group(1) else ""
            func_name = match.group(2)
            
            # Only include functions that don't have Verus-specific keywords
            if not any(kw in keywords for kw in ['spec', 'proof', 'exec', 'open', 'uninterp']):
                # Calculate line number within the original file
                line_number = block_start_line + content_no_comments[:match.start()].count('\n') + 1
                functions.append((func_name, line_number))
        
        # Also check for const functions without Verus keywords
        const_matches = self.const_fn_pattern.finditer(content_no_comments)
        for match in const_matches:
            func_name = match.group(1)
            line_number = block_start_line + content_no_comments[:match.start()].count('\n') + 1
            functions.append((func_name, line_number))
                
        return functions

    def remove_comments(self, content):
        """Remove comments from content to avoid false matches."""
        # Remove line comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove block comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content

    def analyze_file(self, file_path):
        """Analyze a single Rust file for function names and their line numbers."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, PermissionError):
            return []
        
        # Extract all verus blocks
        verus_blocks = self.extract_verus_blocks(content)
        
        if not verus_blocks:
            return []
        
        all_functions = []
        for block_content, block_start_line in verus_blocks:
            functions = self.extract_functions_from_block(block_content, block_start_line)
            all_functions.extend(functions)
        
        return all_functions

    def find_rust_files(self, root_path):
        """Find all Rust files in the given directory."""
        rust_files = []
        for file_path in root_path.rglob('*.rs'):
            if file_path.is_file():
                rust_files.append(file_path)
        return rust_files

    def find_all_functions(self, path):
        """Find all function names in the given path (file or directory)."""
        path = Path(path)
        if not path.exists():
            return {}
        
        all_functions = {}
        
        if path.is_file():
            functions = self.analyze_file(path)
            if functions:
                all_functions[str(path)] = functions
        else:
            rust_files = self.find_rust_files(path)
            for file_path in rust_files:
                functions = self.analyze_file(file_path)
                if functions:
                    all_functions[str(file_path)] = functions
        
        return all_functions

    def categorize_functions_by_verification(self, path, verification_output_file):
        """Categorize functions into verified and failed based on verification output."""
        # Get all functions with their line numbers
        all_functions_with_lines = self.find_all_functions(path)
        
        # Parse verification output
        parser = VerificationParser()
        errors_by_file = parser.parse_verification_output(verification_output_file)
        
        verified_functions = set()
        failed_functions = set()
        
        # Collect all function names
        for file_path, functions in all_functions_with_lines.items():
            for func_name, line_number in functions:
                verified_functions.add(func_name)
        
        # Find functions that failed verification
        for file_path, error_lines in errors_by_file.items():
            for error_line in error_lines:
                failed_func = parser.find_function_at_line(file_path, error_line, all_functions_with_lines)
                if failed_func:
                    failed_functions.add(failed_func)
                    verified_functions.discard(failed_func)
        
        return sorted(list(verified_functions)), sorted(list(failed_functions))


class VerusAnalyzer:
    def __init__(self):
        self.function_finder = RustFunctionFinder()
        self.verification_parser = VerificationParser()
        self.compilation_parser = CompilationErrorParser()
        
    def analyze_output(self, path, output_content, output_file=None, exit_code=None):
        """Comprehensive analysis of Verus verification output."""
        # Parse compilation errors and warnings
        compilation_errors, compilation_warnings = self.compilation_parser.parse_compilation_output(output_content)
        
        # Get all functions (may fail if path doesn't exist or has issues)
        try:
            all_functions_with_lines = self.function_finder.find_all_functions(path)
            all_function_names = set()
            for file_path, functions in all_functions_with_lines.items():
                for func_name, line_number in functions:
                    all_function_names.add(func_name)
        except Exception as e:
            # If we can't analyze functions (e.g., path issues), continue with empty set
            all_functions_with_lines = {}
            all_function_names = set()
        
        # Parse verification results
        if output_file:
            errors_by_file = self.verification_parser.parse_verification_output(output_file)
        else:
            # Create temporary file with output content
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
                temp_file.write(output_content)
                temp_file_path = temp_file.name
            
            errors_by_file = self.verification_parser.parse_verification_output(temp_file_path)
            
            # Clean up temp file
            import os
            os.unlink(temp_file_path)
        
        # Categorize functions
        verified_functions = set(all_function_names)
        failed_functions = set()
        
        # Find functions that failed verification
        for file_path, error_lines in errors_by_file.items():
            for error_line in error_lines:
                failed_func = self.verification_parser.find_function_at_line(file_path, error_line, all_functions_with_lines)
                if failed_func:
                    failed_functions.add(failed_func)
                    verified_functions.discard(failed_func)
        
        # Determine overall status
        has_compilation_errors = len(compilation_errors) > 0
        has_verification_failures = len(failed_functions) > 0
        
        # Check exit code as well - non-zero exit code usually means compilation failure
        if exit_code is not None and exit_code != 0:
            if not has_compilation_errors:
                # If we don't have detected compilation errors but exit code is non-zero,
                # create a generic compilation error
                compilation_errors.append({
                    "message": f"Command failed with exit code {exit_code}",
                    "file": None,
                    "line": None,
                    "column": None,
                    "full_message": [f"Process exited with code {exit_code}"]
                })
                has_compilation_errors = True
        
        if has_compilation_errors:
            status = "compilation_failed"
            # If compilation failed, we can't verify any functions
            verified_functions = set()
            failed_functions = set()
        elif has_verification_failures:
            status = "verification_failed"
        else:
            status = "success"
        
        return {
            "status": status,
            "summary": {
                "total_functions": len(all_function_names),
                "verified_functions": len(verified_functions),
                "failed_functions": len(failed_functions),
                "compilation_errors": len(compilation_errors),
                "compilation_warnings": len(compilation_warnings)
            },
            "compilation": {
                "errors": compilation_errors,
                "warnings": compilation_warnings
            },
            "verification": {
                "verified_functions": sorted(list(verified_functions)),
                "failed_functions": sorted(list(failed_functions))
            },
            "functions_by_file": {
                str(file_path): [{"name": func_name, "line": line_num} for func_name, line_num in functions]
                for file_path, functions in all_functions_with_lines.items()
            }
        }


def main():
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Find and analyze Verus functions')
    parser.add_argument('path', help='Path to search (file or directory)')
    parser.add_argument('--output-file', help='Verification output file to analyze')
    parser.add_argument('--output-content', help='Verification output content as string')
    parser.add_argument('--json-output', help='Output results as JSON to specified file')
    parser.add_argument('--format', choices=['text', 'json'], default='text', 
                       help='Output format (default: text)')
    parser.add_argument('--exit-code', type=int, help='Exit code from the verification command')
    
    args = parser.parse_args()
    
    if args.format == 'json' or args.json_output:
        # JSON output mode
        analyzer = VerusAnalyzer()
        
        if args.output_content:
            # Analyze from content string
            result = analyzer.analyze_output(args.path, args.output_content, exit_code=args.exit_code)
        elif args.output_file:
            # Read output file and analyze
            try:
                with open(args.output_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                result = analyzer.analyze_output(args.path, content, args.output_file, exit_code=args.exit_code)
            except (FileNotFoundError, UnicodeDecodeError, PermissionError) as e:
                print(f"Error reading output file: {e}", file=sys.stderr)
                return 1
        else:
            # No output to analyze, just get function list
            finder = RustFunctionFinder()
            all_functions_with_lines = finder.find_all_functions(args.path)
            all_function_names = set()
            
            for file_path, functions in all_functions_with_lines.items():
                for func_name, line_number in functions:
                    all_function_names.add(func_name)
            
            result = {
                "status": "functions_only",
                "summary": {
                    "total_functions": len(all_function_names),
                    "verified_functions": 0,
                    "failed_functions": 0,
                    "compilation_errors": 0,
                    "compilation_warnings": 0
                },
                "compilation": {
                    "errors": [],
                    "warnings": []
                },
                "verification": {
                    "verified_functions": [],
                    "failed_functions": []
                },
                "all_functions": sorted(list(all_function_names)),
                "functions_by_file": {
                    str(file_path): [{"name": func_name, "line": line_num} for func_name, line_num in functions]
                    for file_path, functions in all_functions_with_lines.items()
                }
            }
        
        if args.json_output:
            with open(args.json_output, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            print(f"JSON output written to {args.json_output}")
        else:
            print(json.dumps(result, indent=2))
    
    else:
        # Original text output behavior
        finder = RustFunctionFinder()
        
        if args.output_file:
            # Categorize functions based on verification results
            verified_functions, failed_functions = finder.categorize_functions_by_verification(args.path, args.output_file)
            
            print("=== VERIFIED FUNCTIONS ===")
            for func_name in verified_functions:
                print(func_name)
            
            print("\n=== FAILED VERIFICATION ===")
            for func_name in failed_functions:
                print(func_name)
                
            print(f"\nSummary: {len(verified_functions)} verified, {len(failed_functions)} failed")
        else:
            # Original behavior - just list all functions
            all_functions_with_lines = finder.find_all_functions(args.path)
            all_function_names = set()
            
            for file_path, functions in all_functions_with_lines.items():
                for func_name, line_number in functions:
                    all_function_names.add(func_name)
            
            # Print all function names, one per line
            for func_name in sorted(all_function_names):
                print(func_name)
    
    return 0


if __name__ == '__main__':
    exit(main())
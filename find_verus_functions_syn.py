#!/usr/bin/env python3
"""
Python script to find all Rust function names inside Verus macros.
This version uses verus_syn (via Rust binary) instead of adhoc regex parsing.

This is a drop-in replacement for find_verus_functions.py with the same API,
but using proper AST parsing via verus_syn for more accurate results.
"""

import re
import json
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional

# Import the verus_syn wrapper
from verus_parser_wrapper import VerusParser


class CompilationErrorParser:
    """Parse compilation errors from cargo/verus output (unchanged from original)."""
    
    def __init__(self):
        # Pattern to match compilation errors - improved for Cargo output
        self.error_pattern = re.compile(r'error(?:\[E\d+\])?: (.+)')
        self.cargo_error_pattern = re.compile(r'error: could not compile `([^`]+)`')
        self.warning_pattern = re.compile(r'warning: (.+)')
        self.file_location_pattern = re.compile(r'-->\s+([^:]+):(\d+):(\d+)')
        self.process_error_pattern = re.compile(r"process didn't exit successfully: (.+)")
        self.memory_error_pattern = re.compile(r'memory allocation of \d+ bytes failed')
        self.caused_by_pattern = re.compile(r'Caused by:')
        self.exit_status_pattern = re.compile(r'\(exit status: (\d+)\)')
        self.verus_command_exit_pattern = re.compile(r'Verus command completed with exit code: (\d+)')
        self.verification_results_pattern = re.compile(r'verification results::\s*(\d+)\s+verified,\s*(\d+)\s+errors?')
        self.verification_error_patterns = [
            re.compile(r'error: assertion failed'),
            re.compile(r'error: postcondition not satisfied'),
            re.compile(r'error: precondition not satisfied'),
            re.compile(r'error: loop invariant not preserved'),
            re.compile(r'error: loop invariant not satisfied on entry'),
            re.compile(r'error: assertion not satisfied'),
        ]
    
    def parse_compilation_output(self, output_content):
        """Parse compilation output and extract errors and warnings."""
        errors = []
        warnings = []
        current_error = None
        current_warning = None
        has_verification_results = False
        
        lines = output_content.split('\n')
        
        # First pass: check if we have verification results
        for line in lines:
            line = line.strip()
            if self.verification_results_pattern.search(line):
                has_verification_results = True
                break
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Check for verification results summary
            verification_results_match = self.verification_results_pattern.search(line)
            if verification_results_match:
                continue
            
            # Check for cargo compilation errors
            cargo_error_match = self.cargo_error_pattern.search(line)
            if cargo_error_match:
                if has_verification_results:
                    continue
                    
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
            
            # Check for Verus command exit code messages
            verus_exit_match = self.verus_command_exit_pattern.search(line)
            if verus_exit_match:
                exit_code = int(verus_exit_match.group(1))
                if current_error:
                    current_error["full_message"].append(line)
                    current_error["message"] += f" (exit code: {exit_code})"
                else:
                    current_error = {
                        "message": f"Verus command failed with exit code {exit_code}",
                        "file": None,
                        "line": None,
                        "column": None,
                        "full_message": [line]
                    }
                continue
            
            # Check for process failure errors
            process_error_match = self.process_error_pattern.search(line)
            if process_error_match:
                if current_error:
                    current_error["full_message"].append(line)
                    current_error["message"] += f" - {process_error_match.group(1)}"
                else:
                    current_error = {
                        "message": f"Process execution failed: {process_error_match.group(1)}",
                        "file": None,
                        "line": None,
                        "column": None,
                        "full_message": [line]
                    }
                continue
            
            # Check for standard error format
            error_match = self.error_pattern.search(line)
            if error_match:
                is_verification_error = any(pattern.search(line) for pattern in self.verification_error_patterns)
                
                if is_verification_error:
                    continue
                
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
            
            # Add continuation lines
            if current_error and (line.startswith('|') or line.startswith('^') or line.startswith('=') or 
                                line.startswith('Caused by:') or line.startswith('(signal:') or 
                                line.startswith('  process didn\'t exit successfully:') or 
                                self.exit_status_pattern.search(line)):
                current_error["full_message"].append(line)
                if line.startswith('Caused by:'):
                    current_error["message"] += f" - {line.strip()}"
                elif '(signal:' in line:
                    current_error["message"] += f" - {line.strip()}"
                elif self.exit_status_pattern.search(line):
                    exit_match = self.exit_status_pattern.search(line)
                    if exit_match:
                        current_error["message"] += f" (exit status: {exit_match.group(1)})"
            elif current_warning and (line.startswith('|') or line.startswith('^') or line.startswith('=')):
                current_warning["full_message"].append(line)
            elif line == "":
                if current_error and len(current_error["full_message"]) > 0:
                    errors.append(current_error)
                    current_error = None
                if current_warning and len(current_warning["full_message"]) > 0:
                    warnings.append(current_warning)
                    current_warning = None
        
        if current_error:
            errors.append(current_error)
        if current_warning:
            warnings.append(current_warning)
            
        return errors, warnings
    
    def has_verification_results(self, output_content):
        """Check if the output contains verification results summary."""
        return self.verification_results_pattern.search(output_content) is not None


class VerificationParser:
    """Parse verification results (unchanged from original)."""
    
    def __init__(self):
        self.error_pattern = re.compile(r'-->\s+([^:]+):(\d+):\d+')
        self.verification_failure_pattern = re.compile(r'error.*assertion failed')
        self.verification_error_types = [
            'assertion failed',
            'postcondition not satisfied', 
            'precondition not satisfied',
            'loop invariant not preserved',
            'loop invariant not satisfied on entry',
            'assertion not satisfied'
        ]
    
    def parse_verification_output(self, output_file_path):
        """Parse verification output and extract files with errors and their line numbers."""
        try:
            with open(output_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (FileNotFoundError, UnicodeDecodeError, PermissionError):
            return {}
        
        return self.parse_verification_output_from_content(content)

    def parse_verification_output_from_content(self, output_content):
        """Parse verification output content and extract files with errors and their line numbers."""
        errors_by_file = {}
        lines = output_content.split('\n')
        
        for i, line in enumerate(lines):
            match = self.error_pattern.search(line)
            if match:
                file_path = match.group(1)
                line_number = int(match.group(2))
                
                is_actual_error = False
                
                for j in range(max(0, i - 10), i):
                    prev_line = lines[j].strip()
                    
                    if prev_line.startswith('error:') or prev_line.startswith('error['):
                        if not (prev_line.startswith('note:') or 'has been running for' in prev_line or 
                               'finished in' in prev_line or 'check has been running' in prev_line or
                               'check finished in' in prev_line):
                            is_actual_error = True
                            break
                    
                    if (prev_line.startswith('note:') and 
                        ('has been running for' in prev_line or 'finished in' in prev_line or
                         'check has been running' in prev_line or 'check finished in' in prev_line)):
                        is_actual_error = False
                        break
                
                if is_actual_error:
                    if file_path not in errors_by_file:
                        errors_by_file[file_path] = []
                    errors_by_file[file_path].append(line_number)
        
        return errors_by_file

    def parse_verification_failures(self, output_content):
        """Parse verification failures and return detailed information."""
        failures = []
        lines = output_content.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            failure_detected = False
            error_type = None
            for error_type_pattern in self.verification_error_types:
                if error_type_pattern in line:
                    failure_detected = True
                    error_type = error_type_pattern
                    break
            
            if failure_detected and 'error' in line.lower():
                error_start_line = i
                file_path = None
                line_number = None
                column = None
                
                full_error_lines = []
                location_found_at = -1
                
                for j in range(i, min(i + 15, len(lines))):
                    current_line = lines[j]
                    full_error_lines.append(current_line)
                    
                    match = self.error_pattern.search(current_line)
                    if match and location_found_at == -1:
                        file_path = match.group(1)
                        line_number = int(match.group(2))
                        location_found_at = j
                        
                        try:
                            parts = current_line.split(':')
                            if len(parts) >= 3:
                                column = int(parts[-1])
                        except (ValueError, IndexError):
                            pass
                    
                    if location_found_at != -1 and j > location_found_at + 1:
                        next_line = current_line.strip()
                        if next_line == "" and j + 1 < len(lines):
                            next_next_line = lines[j + 1].strip() if j + 1 < len(lines) else ""
                            if next_next_line.startswith('error:') or next_next_line.startswith('verification results') or \
                               next_next_line.startswith('note:'):
                                break
                
                clean_full_text = []
                for line_text in full_error_lines:
                    clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line_text.rstrip())
                    clean_full_text.append(clean_line)
                
                complete_error_text = '\n'.join(clean_full_text).strip()
                
                assertion_details = []
                for line_text in clean_full_text:
                    clean_line = line_text.strip()
                    if clean_line and ('assert' in clean_line or '|' in clean_line or clean_line.startswith('-->')):
                        assertion_details.append(clean_line)
                
                clean_file_path = re.sub(r'\x1b\[[0-9;]*m', '', file_path) if file_path else None
                clean_message = re.sub(r'\x1b\[[0-9;]*m', '', line.strip())
                
                failure = {
                    "error_type": error_type,
                    "file": clean_file_path,
                    "line": line_number,
                    "column": column,
                    "message": clean_message,
                    "assertion_details": assertion_details[:10],
                    "full_error_text": complete_error_text
                }
                
                failures.append(failure)
            
            i += 1
        
        return failures
    
    def find_function_at_line(self, file_path, line_number, all_functions_with_lines):
        """Find the function that contains or is closest above the given line number."""
        matching_file = None
        file_path_normalized = str(Path(file_path))
        
        for file_key in all_functions_with_lines.keys():
            file_key_normalized = str(Path(file_key))
            
            if file_path_normalized == file_key_normalized:
                matching_file = file_key
                break
            
            if file_path_normalized.endswith(file_key_normalized) or file_key_normalized.endswith(file_path_normalized):
                matching_file = file_key
                break
            
            if file_path_normalized in file_key_normalized or file_key_normalized in file_path_normalized:
                matching_file = file_key
                break
            
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
    """Find Rust functions using verus_syn instead of regex."""
    
    def __init__(self, include_verus_constructs=False):
        self.include_verus_constructs = include_verus_constructs
        try:
            self.parser = VerusParser()
        except FileNotFoundError as e:
            print(f"Warning: {e}", file=sys.stderr)
            print("Falling back to basic mode (no function parsing available)", file=sys.stderr)
            self.parser = None

    def analyze_file(self, file_path):
        """Analyze a single Rust file for function names and their line numbers."""
        if self.parser is None:
            return []
        
        try:
            data = self.parser.parse_functions(
                str(file_path),
                include_verus_constructs=self.include_verus_constructs,
                include_methods=True
            )
            return [(func["name"], func["start_line"]) for func in data["functions"]]
        except Exception as e:
            print(f"Warning: Failed to parse {file_path}: {e}", file=sys.stderr)
            return []

    def find_all_functions(self, path):
        """Find all function names in the given path (file or directory)."""
        if self.parser is None:
            return {}
        
        try:
            return self.parser.find_all_functions(
                str(path),
                include_verus_constructs=self.include_verus_constructs
            )
        except Exception as e:
            print(f"Warning: Failed to parse functions: {e}", file=sys.stderr)
            return {}

    def categorize_functions_by_verification(self, path, verification_output_file):
        """Categorize functions into verified and failed based on verification output."""
        all_functions_with_lines = self.find_all_functions(path)
        
        parser = VerificationParser()
        errors_by_file = parser.parse_verification_output(verification_output_file)
        
        verified_functions = set()
        failed_functions = set()
        
        for file_path, functions in all_functions_with_lines.items():
            for func_name, line_number in functions:
                verified_functions.add(func_name)
        
        for file_path, error_lines in errors_by_file.items():
            for error_line in error_lines:
                failed_func = parser.find_function_at_line(file_path, error_line, all_functions_with_lines)
                if failed_func:
                    failed_functions.add(failed_func)
                    verified_functions.discard(failed_func)
        
        return sorted(list(verified_functions)), sorted(list(failed_functions))


class VerusRunner:
    """Runs cargo verus verification and captures output (unchanged from original)."""
    
    def __init__(self):
        pass
    
    def setup_environment(self):
        """Set up environment variables for Verus verification."""
        import os
        
        boring_stub = '/tmp/boring-stub'
        Path(boring_stub).mkdir(parents=True, exist_ok=True)
        Path(f'{boring_stub}/lib').mkdir(exist_ok=True)
        Path(f'{boring_stub}/include').mkdir(exist_ok=True)
        
        os.environ['BORING_BSSL_PATH'] = boring_stub
        os.environ['BORING_BSSL_ASSUME_PATCHED'] = '1'
        os.environ['DOCS_RS'] = '1'
    
    def run_verification(self, work_dir, package=None, module=None, function=None, extra_args=None):
        """Run cargo verus verification and return output and exit code."""
        import subprocess
        import os
        
        original_dir = os.getcwd()
        
        try:
            os.chdir(work_dir)
            self.setup_environment()
            
            cmd = ['cargo', 'verus', 'verify']
            
            if package:
                cmd.extend(['-p', package])
            
            verus_args = []
            if module:
                verus_args.extend(['--verify-only-module', module])
            if function:
                verus_args.extend(['--verify-function', function])
            
            if verus_args:
                cmd.append('--')
                cmd.extend(verus_args)
            
            if extra_args:
                cmd.extend(extra_args)
            
            print(f"Running: {' '.join(cmd)}")
            print(f"Working directory: {os.getcwd()}")
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            return result.stdout, result.returncode
            
        finally:
            os.chdir(original_dir)


class VerusAnalyzer:
    """Analyze Verus verification results."""
    
    def __init__(self, include_verus_constructs=False):
        self.function_finder = RustFunctionFinder(include_verus_constructs=include_verus_constructs)
        self.verification_parser = VerificationParser()
        self.compilation_parser = CompilationErrorParser()
    
    def filter_functions_by_module_and_function(self, all_functions_with_lines, functions_set, module_filter=None, function_filter=None):
        """Filter functions based on module and/or function name filters."""
        if not module_filter and not function_filter:
            return functions_set
        
        filtered_functions = set()
        
        if module_filter:
            module_path = module_filter.replace('::', '/')
            
        for file_path, functions in all_functions_with_lines.items():
            file_path_str = str(file_path)
            
            if module_filter:
                if not (f"/{module_path}.rs" in file_path_str or f"/{module_path}/" in file_path_str):
                    continue
            
            for func_name, line_number in functions:
                if func_name not in functions_set:
                    continue
                    
                if function_filter and func_name != function_filter:
                    continue
                
                filtered_functions.add(func_name)
        
        return filtered_functions
        
    def analyze_output(self, path, output_content, output_file=None, exit_code=None, module_filter=None, function_filter=None):
        """Comprehensive analysis of Verus verification output."""
        compilation_errors, compilation_warnings = self.compilation_parser.parse_compilation_output(output_content)
        
        try:
            all_functions_with_lines = self.function_finder.find_all_functions(path)
            all_function_names = set()
            for file_path, functions in all_functions_with_lines.items():
                for func_name, line_number in functions:
                    all_function_names.add(func_name)
        except Exception as e:
            all_functions_with_lines = {}
            all_function_names = set()
        
        if output_file:
            errors_by_file = self.verification_parser.parse_verification_output(output_file)
        else:
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
                temp_file.write(output_content)
                temp_file_path = temp_file.name
            
            errors_by_file = self.verification_parser.parse_verification_output(temp_file_path)
            os.unlink(temp_file_path)
        
        verification_failures = self.verification_parser.parse_verification_failures(output_content)
        
        verified_functions = set(all_function_names)
        failed_functions = set()
        
        for file_path, error_lines in errors_by_file.items():
            for error_line in error_lines:
                failed_func = self.verification_parser.find_function_at_line(file_path, error_line, all_functions_with_lines)
                if failed_func:
                    failed_functions.add(failed_func)
                    verified_functions.discard(failed_func)
        
        for failure in verification_failures:
            if failure.get('file') and failure.get('line'):
                failed_func = self.verification_parser.find_function_at_line(
                    failure['file'], failure['line'], all_functions_with_lines
                )
                if failed_func:
                    failed_functions.add(failed_func)
                    verified_functions.discard(failed_func)
        
        has_compilation_errors = len(compilation_errors) > 0
        has_verification_failures = len(verification_failures) > 0
        has_verification_results = self.compilation_parser.has_verification_results(output_content)
        
        if exit_code is not None and exit_code != 0:
            if not has_compilation_errors and not has_verification_failures and not has_verification_results:
                compilation_errors.append({
                    "message": f"Command failed with exit code {exit_code}",
                    "file": None,
                    "line": None,
                    "column": None,
                    "full_message": [f"Process exited with code {exit_code}"]
                })
                has_compilation_errors = True
        
        if has_verification_results:
            if has_verification_failures:
                status = "verification_failed"
            else:
                status = "success"
        elif has_compilation_errors:
            status = "compilation_failed"
            verified_functions = set()
            failed_functions = set()
        else:
            status = "success"
        
        if module_filter or function_filter:
            verified_functions = self.filter_functions_by_module_and_function(
                all_functions_with_lines, verified_functions, module_filter, function_filter
            )
            failed_functions = self.filter_functions_by_module_and_function(
                all_functions_with_lines, failed_functions, module_filter, function_filter
            )
            
            all_function_names = self.filter_functions_by_module_and_function(
                all_functions_with_lines, all_function_names, module_filter, function_filter
            )
        
        return {
            "status": status,
            "summary": {
                "total_functions": len(all_function_names),
                "verified_functions": len(verified_functions),
                "failed_functions": len(failed_functions),
                "compilation_errors": len(compilation_errors),
                "compilation_warnings": len(compilation_warnings),
                "verification_errors": len(verification_failures)
            },
            "compilation": {
                "errors": compilation_errors,
                "warnings": compilation_warnings
            },
            "verification": {
                "verified_functions": sorted(list(verified_functions)),
                "failed_functions": sorted(list(failed_functions)),
                "errors": verification_failures
            },
            "functions_by_file": {
                str(file_path): [{"name": func_name, "line": line_num} for func_name, line_num in functions]
                for file_path, functions in all_functions_with_lines.items()
            }
        }


def main():
    parser = argparse.ArgumentParser(
        description='Run Verus verification and analyze results (using verus_syn parser)',
        epilog='''
Examples:
  # Run verification and generate JSON report
  %(prog)s /path/to/project --run-verification --json-output report.json
  
  # Run verification for specific module
  %(prog)s /path/to/project --run-verification --verify-only-module my::module --json-output report.json
  
  # Analyze existing verification output
  %(prog)s /path/to/project --output-file verus_output.txt --json-output report.json
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('path', help='Path to search (file or directory)')
    
    # Verification runner options
    parser.add_argument('--run-verification', action='store_true',
                       help='Run cargo verus verification before analysis')
    parser.add_argument('--package', '-p', help='Package to verify (for workspace projects)')
    parser.add_argument('--verify-only-module', help='Module to verify (e.g., backend::serial::u64::field_verus)')
    parser.add_argument('--verify-function', help='Function to verify')
    
    # Analysis options
    parser.add_argument('--output-file', help='Verification output file to analyze (alternative to --run-verification)')
    parser.add_argument('--output-content', help='Verification output content as string')
    parser.add_argument('--exit-code', type=int, help='Exit code from the verification command')
    
    # Output options
    parser.add_argument('--json-output', help='Output results as JSON to specified file')
    parser.add_argument('--format', choices=['text', 'json'], default='text', 
                       help='Output format (default: text)')
    parser.add_argument('--exclude-verus-constructs', action='store_true',
                       help='Exclude Verus constructs (spec, proof, exec) and only include regular functions')
    
    args = parser.parse_args()
    
    verification_output = None
    verification_exit_code = None
    
    if args.run_verification:
        print("=" * 60)
        print("Running Verus verification...")
        print("=" * 60)
        
        runner = VerusRunner()
        verification_output, verification_exit_code = runner.run_verification(
            work_dir=args.path,
            package=args.package,
            module=args.verify_only_module,
            function=args.verify_function
        )
        
        print("\n" + "=" * 60)
        print(f"Verification completed with exit code: {verification_exit_code}")
        print("=" * 60 + "\n")
        
        if 'verification results::' in verification_output:
            if ', 0 errors' in verification_output:
                print("✓ Verification succeeded!")
            else:
                print("✗ Verification failed with errors")
        elif verification_exit_code != 0:
            print("✗ Compilation or verification failed")
    
    if args.format == 'json' or args.json_output:
        analyzer = VerusAnalyzer(include_verus_constructs=not args.exclude_verus_constructs)
        
        if verification_output is not None:
            result = analyzer.analyze_output(
                args.path, verification_output, 
                exit_code=verification_exit_code,
                module_filter=args.verify_only_module, 
                function_filter=args.verify_function
            )
        elif args.output_content:
            result = analyzer.analyze_output(args.path, args.output_content, exit_code=args.exit_code, 
                                           module_filter=args.verify_only_module, function_filter=args.verify_function)
        elif args.output_file:
            try:
                with open(args.output_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                result = analyzer.analyze_output(args.path, content, args.output_file, exit_code=args.exit_code,
                                                module_filter=args.verify_only_module, function_filter=args.verify_function)
            except (FileNotFoundError, UnicodeDecodeError, PermissionError) as e:
                print(f"Error reading output file: {e}", file=sys.stderr)
                return 1
        else:
            finder = RustFunctionFinder(include_verus_constructs=not args.exclude_verus_constructs)
            all_functions_with_lines = finder.find_all_functions(args.path)
            all_function_names = set()
            
            for file_path, functions in all_functions_with_lines.items():
                for func_name, line_number in functions:
                    all_function_names.add(func_name)
            
            if args.verify_only_module or args.verify_function:
                analyzer = VerusAnalyzer(include_verus_constructs=not args.exclude_verus_constructs)
                all_function_names = analyzer.filter_functions_by_module_and_function(
                    all_functions_with_lines, all_function_names, args.verify_only_module, args.verify_function
                )
            
            result = {
                "status": "functions_only",
                "summary": {
                    "total_functions": len(all_function_names),
                    "verified_functions": 0,
                    "failed_functions": 0,
                    "compilation_errors": 0,
                    "compilation_warnings": 0,
                    "verification_errors": 0
                },
                "compilation": {
                    "errors": [],
                    "warnings": []
                },
                "verification": {
                    "verified_functions": [],
                    "failed_functions": [],
                    "errors": []
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
        finder = RustFunctionFinder(include_verus_constructs=not args.exclude_verus_constructs)
        
        if verification_output is not None:
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
                temp_file.write(verification_output)
                temp_file_path = temp_file.name
            
            try:
                verified_functions, failed_functions = finder.categorize_functions_by_verification(args.path, temp_file_path)
                
                print("=== VERIFIED FUNCTIONS ===")
                for func_name in verified_functions:
                    print(func_name)
                
                print("\n=== FAILED VERIFICATION ===")
                for func_name in failed_functions:
                    print(func_name)
                    
                print(f"\nSummary: {len(verified_functions)} verified, {len(failed_functions)} failed")
            finally:
                os.unlink(temp_file_path)
        elif args.output_file:
            verified_functions, failed_functions = finder.categorize_functions_by_verification(args.path, args.output_file)
            
            print("=== VERIFIED FUNCTIONS ===")
            for func_name in verified_functions:
                print(func_name)
            
            print("\n=== FAILED VERIFICATION ===")
            for func_name in failed_functions:
                print(func_name)
                
            print(f"\nSummary: {len(verified_functions)} verified, {len(failed_functions)} failed")
        else:
            all_functions_with_lines = finder.find_all_functions(args.path)
            all_function_names = set()
            
            for file_path, functions in all_functions_with_lines.items():
                for func_name, line_number in functions:
                    all_function_names.add(func_name)
            
            for func_name in sorted(all_function_names):
                print(func_name)
    
    return 0


if __name__ == '__main__':
    exit(main())


# Verus Verification Docker Container

This Docker container provides a complete environment for running Verus verification on Rust projects. It includes Ubuntu 22.04, Rust 1.88.0, and the latest version of Verus.

The container automatically handles module resolution issues by building the project before verification, making it especially useful for workspace projects.

## Quick Start

### Using Pre-built Images (Recommended)

Pre-built images are available from GitHub Container Registry and are automatically updated with the latest Verus releases:

```bash
# Pull latest stable release
docker pull ghcr.io/beneficial-ai-foundation/dockerfile_verus:latest

# Pull latest prerelease
docker pull ghcr.io/beneficial-ai-foundation/dockerfile_verus:prerelease

# Pull specific version
docker pull ghcr.io/beneficial-ai-foundation/dockerfile_verus:v1.0.0
```

### Build the Docker Image Locally

If you prefer to build locally or need customizations:

```bash
# Build with latest stable release (default)
docker build -f Dockerfile.verus -t verus-verifier-stable .

# Build with latest Verus prerelease
docker build -f Dockerfile.verus --build-arg VERUS_RELEASE_TYPE=prerelease -t verus-verifier-prerelease .
```

### Basic Usage

```bash
# Verify entire project (using pre-built image)
docker run --rm -v /path/to/project:/workspace ghcr.io/beneficial-ai-foundation/dockerfile_verus:latest \
  /usr/local/bin/verify-verus.sh --work-dir /workspace

# Verify specific module
docker run --rm -v /path/to/project:/workspace ghcr.io/beneficial-ai-foundation/dockerfile_verus:latest \
  /usr/local/bin/verify-verus.sh --work-dir /workspace \
  --verify-only-module module::path::name

# Verify specific function within a module
docker run --rm -v /path/to/project:/workspace ghcr.io/beneficial-ai-foundation/dockerfile_verus:latest \
  /usr/local/bin/verify-verus.sh --work-dir /workspace \
  --verify-only-module module::path::name \
  --verify-function function_name

# Generate JSON report with verification results
docker run --rm -v /path/to/project:/workspace ghcr.io/beneficial-ai-foundation/dockerfile_verus:latest \
  /usr/local/bin/verify-verus.sh --work-dir /workspace \
  --json-output /workspace/verification_report.json

# Use prerelease version for latest features
docker run --rm -v /path/to/project:/workspace ghcr.io/beneficial-ai-foundation/dockerfile_verus:prerelease \
  /usr/local/bin/verify-verus.sh --work-dir /workspace
```

### Example: curve25519-dalek

```bash
# Verify entire project
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace ghcr.io/beneficial-ai-foundation/dockerfile_verus:latest \
  /usr/local/bin/verify-verus.sh --work-dir /workspace/curve25519-dalek

# Verify specific module
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier-stable \
  /usr/local/bin/verify-verus.sh --work-dir /workspace/curve25519-dalek \
  --verify-only-module backend::serial::u64::field_verus

# Verify specific function (pow2k) in module
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier-stable \
  /usr/local/bin/verify-verus.sh --work-dir /workspace/curve25519-dalek \
  --verify-only-module backend::serial::u64::field_verus \
  --verify-function pow2k

# Generate comprehensive JSON report
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier-stable \
  /usr/local/bin/verify-verus.sh --work-dir /workspace/curve25519-dalek \
  --json-output /workspace/curve25519_verification.json
```

## Parameters

- `--work-dir`: The working directory inside the container (usually a subdirectory of /workspace)
- `--verify-only-module`: Specify a single module to verify
- `--verify-function`: Specify a single function to verify (requires --verify-only-module)
- `--package` or `-p`: For workspace projects, specify which package to verify
- `--json-output`: Generate a comprehensive JSON report with verification results

## JSON Output Format

When using `--json-output`, the script generates a detailed JSON report containing:

```json
{
  "status": "success|compilation_failed|verification_failed",
  "summary": {
    "total_functions": 42,
    "verified_functions": 35,
    "failed_functions": 7,
    "compilation_errors": 0,
    "compilation_warnings": 2
  },
  "compilation": {
    "errors": [
      {
        "message": "error description",
        "file": "src/example.rs",
        "line": 123,
        "column": 45,
        "full_message": ["full error context..."]
      }
    ],
    "warnings": [...]
  },
  "verification": {
    "verified_functions": ["func1", "func2", ...],
    "failed_functions": ["func3", "func4", ...]
  },
  "functions_by_file": {
    "src/example.rs": [
      {"name": "func_name", "line": 10}
    ]
  }
}
```

## Features

- **Automatic Build**: The script runs `cargo build` before verification to ensure module resolution works correctly
- **Workspace Support**: Handles Rust workspace projects with multiple crates
- **Debug Output**: Shows the command being executed, working directory, and Verus version
- **Module Resolution Fix**: Solves the "could not find module" error when running in Docker containers
- **JSON Reporting**: Generate comprehensive JSON reports with compilation errors and verification results
- **Function Analysis**: Automatically categorize functions as verified or failed based on Verus output

## Container Details

- **Base Image**: Ubuntu 22.04
- **Rust Version**: 1.88.0
- **Verus**: Latest release (stable by default, or prerelease via build arg)
- **Working Directory**: `/workspace` (mount your project here)
- **Architecture**: amd64/x86_64 only (other systems can be supported if need be)

## Automated Builds & Releases

Images are automatically built and published to GitHub Container Registry:

- **Triggers**: 
  - New commits to master branch
  - New version tags
  - Weekly schedule (to get latest Verus releases)
  - Manual dispatch

- **Available Tags**:
  - `latest` - Latest stable Verus release
  - `stable` - Latest stable Verus release  
  - `prerelease` - Latest Verus prerelease
  - `v1.0.0` - Specific tagged versions
  - `v1.0.0-prerelease` - Prerelease variants of tagged versions

The containers are automatically updated weekly to include the latest Verus releases.

## Troubleshooting

### Module Not Found Error

If you get "could not find module" errors, the script automatically runs `cargo build` before verification to resolve this issue. This is especially important for workspace projects.

### Interactive Debugging

```bash
# Open a bash shell in the container
docker run --rm -it -v /path/to/project:/workspace verus-verifier-stable bash

# Check Verus version
docker run --rm verus-verifier-stable /root/.cargo/bin/verus-x86-linux/verus --version
```

## Repository Structure

- `Dockerfile.verus`: The Docker image definition
- `verify-verus.sh`: Verification script with automatic build and module/function selection
- `find_verus_functions.py`: Python script for analyzing Verus output and generating JSON reports
- `README.md`: This documentation


### Concrete examples

`docker build -f Dockerfile.verus -t verus-verifier .`

`docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier   /usr/local/bin/verify-verus.sh --work-dir /workspace/curve25519-dalek --verify-only-module backend::serial::u64::field_verus --json-output /workspace/verification_report.json`

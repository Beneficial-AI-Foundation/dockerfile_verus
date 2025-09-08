# Verus Verification Docker Container

This Docker container provides a complete environment for running Verus verification on Rust projects. It includes Ubuntu 22.04, Rust 1.88.0, and the latest version of Verus.

The container automatically handles module resolution issues by building the project before verification, making it especially useful for workspace projects.

## Quick Start

### Download Pre-built Images

Ready-to-use Docker images are available for download from the [GitHub Releases page](https://github.com/beneficial-ai-foundation/dockerfile_verus/releases):

- **`verus-docker-stable-vX.X.X.tar.gz`** - Stable Verus release (recommended)
- **`verus-docker-prerelease-vX.X.X.tar.gz`** - Latest Verus prerelease
- **`install.sh`** - Automated installation script (also available in this repository)

**Quick installation:**

```bash
# Option 1: Download install.sh from releases, then:
chmod +x install.sh
./install.sh

# Option 2: Use install.sh from this repository:
wget https://raw.githubusercontent.com/beneficial-ai-foundation/dockerfile_verus/master/install.sh
chmod +x install.sh
./install.sh
```

**Manual installation:**

```bash
# Download and load the image
docker load < verus-docker-stable-v1.0.0.tar.gz

# Verify a project  
docker run --rm -v /path/to/project:/workspace ghcr.io/beneficial-ai-foundation/dockerfile_verus:stable \
  /usr/local/bin/verify-verus.sh --work-dir /workspace
```

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

# Build with specific Verus revision (useful for reproducible builds)
docker build -f Dockerfile.verus --build-arg VERUS_RELEASE_TYPE=33c6cec7bd19818e51d2b61f629d5d2484778bed -t verus-verifier-revision .

# Use the helper script for building with revisions
./build-revision.sh 33c6cec7bd19818e51d2b61f629d5d2484778bed verus-revision

# Force rebuild without cache to get latest Verus version
docker build --no-cache -f Dockerfile.verus -t verus-verifier-stable .
```

#### Build Arguments

- `VERUS_RELEASE_TYPE`: Controls which version of Verus to install
  - `stable` (default): Latest stable release
  - `prerelease`: Latest prerelease
  - `<commit_hash>`: Specific git revision (40-character hex string)
    - Example: `33c6cec7bd19818e51d2b61f629d5d2484778bed`
    - The build will automatically find the corresponding release for the revision

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

# Use specific revision (for reproducible verification)
docker run --rm -v /path/to/project:/workspace verus-verifier-revision \
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

### Using Specific Revisions for Reproducible Builds

Some projects require specific Verus versions. For example, if your `Cargo.toml` specifies:

```toml
vstd = { git = "https://github.com/verus-lang/verus", rev = "33c6cec7bd19818e51d2b61f629d5d2484778bed"}
```

You can build a Docker image with that exact Verus version:

```bash
# Build with specific revision matching your Cargo.toml
docker build -f Dockerfile.verus --build-arg VERUS_RELEASE_TYPE=33c6cec7bd19818e51d2b61f629d5d2484778bed -t verus-curve25519 .

# Or use the helper script
./build-revision.sh 33c6cec7bd19818e51d2b61f629d5d2484778bed verus-curve25519

# Then verify with the matching version
docker run --rm -v /path/to/project:/workspace verus-curve25519 \
  /usr/local/bin/verify-verus.sh --work-dir /workspace
```

The build process automatically finds the release that corresponds to the revision (e.g., `release/0.2025.08.01.33c6cec`) and downloads the pre-built binary instead of building from source.

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

Images and downloadable packages are automatically built and published:

- **Docker Images**: Published to GitHub Container Registry
- **Pre-built Image Files**: Available on the [GitHub Releases page](https://github.com/beneficial-ai-foundation/dockerfile_verus/releases)

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

- **Release Downloads**:
  - `verus-docker-stable-vX.X.X.tar.gz` - Pre-built stable image
  - `verus-docker-prerelease-vX.X.X.tar.gz` - Pre-built prerelease image
  - `verus-docker-source-vX.X.X.tar.gz` - Source code for customization
  - `install.sh` - Automated installation script

**Note**: The containers are automatically made public after publishing, so no authentication is required for pulling.

The containers are automatically updated weekly to include the latest Verus releases.

## Troubleshooting

### Docker Permission Issues

If you get permission denied errors when running Docker commands:

```bash
# Option 1: Add your user to the docker group (requires logout/login)
sudo usermod -aG docker $USER

# Option 2: Run with sudo (temporary solution)
sudo docker pull ghcr.io/beneficial-ai-foundation/dockerfile_verus:latest
```

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
- `build-revision.sh`: Helper script for building Docker images with specific Verus revisions
- `install.sh`: Automated installer for pre-built Docker images
- `README.md`: This documentation


### Concrete examples

`docker build -f Dockerfile.verus -t verus-verifier .`

`docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier   /usr/local/bin/verify-verus.sh --work-dir /workspace/curve25519-dalek --verify-only-module backend::serial::u64::field_verus --json-output /workspace/verification_report.json`

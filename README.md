# Verus Verification Docker Container

This Docker container provides a complete environment for running Verus verification on a given project. It includes Ubuntu 22.04, Rust 1.88.0, and the latest version of Verus.

**Recommended Usage**: Use volume mounting to work with your local project files directly.

## Building the Docker Image

Build the Docker image once:

```bash
docker build -f Dockerfile.verus -t verus-verifier .
```

## Running the Container

### Basic Usage

Mount your project directory directly into the container:

```bash
# Mount your project directory to /workspace (default verification)
docker run --rm -v /path/to/your/verus-project:/workspace verus-verifier

# For interactive development and debugging
docker run --rm -it -v /path/to/your/verus-project:/workspace verus-verifier bash
```

### Module-Specific Verification

Verify specific modules using the `--verify-only-module` option:

```bash
# Verify a specific module
docker run --rm -v /path/to/your/verus-project:/workspace verus-verifier \
  /usr/local/bin/verify-verus.sh --verify-only-module <module>
```

### Projects with Nested Directory Structure

For projects like curve25519-dalek where you need to mount the parent directory but run commands from a subdirectory:

```bash
# Mount parent directory and specify working directory
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier \
  /usr/local/bin/verify-verus.sh --work-dir /workspace/curve25519-dalek

# Combine with module-specific verification
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier \
  /usr/local/bin/verify-verus.sh --work-dir /workspace/curve25519-dalek --verify-only-module backend::serial::u64::field_verus
```

### Custom Verification Commands

The container also supports running custom Verus commands directly:

```bash
# Run verification with specific flags
docker run --rm -v /path/to/your/verus-project:/workspace verus-verifier cargo verus verify --verbose

# Run verification on specific modules (alternative syntax)
docker run --rm -v /path/to/your/verus-project:/workspace verus-verifier \
  cargo verus verify -- --verify-only-module your::module::path

# Run other cargo commands
docker run --rm -v /path/to/your/verus-project:/workspace verus-verifier cargo build
```

## Script Options

The included `/usr/local/bin/verify-verus.sh` script supports the following options:

- `--work-dir <path>`: Change to specified directory before running verification (default: `/workspace`)
- `--verify-only-module <module>`: Verify only the specified module
- Additional arguments are passed through to the cargo verus command

## Example Use Cases

### Standard Project
```bash
docker run --rm -v /path/to/project:/workspace verus-verifier
```

### Nested Project Structure
```bash
docker run --rm -v /path/to/parent:/workspace verus-verifier \
  /usr/local/bin/verify-verus.sh --work-dir /workspace/subproject
```

### Module-Specific Verification
```bash
docker run --rm -v /path/to/project:/workspace verus-verifier \
  /usr/local/bin/verify-verus.sh --verify-only-module my::module::path
```

## Container Details

- **Base Image**: Ubuntu 22.04
- **Rust Version**: 1.88.0
- **Verus**: Latest release (automatically downloaded during build)
- **Working Directory**: `/workspace` (mount your project here)
- **Default Command**: `cargo verus verify`

## Environment Variables

The container sets the following environment variables:
- `DEBIAN_FRONTEND=noninteractive`
- `CARGO_TERM_COLOR=always`
- `RUSTFLAGS='-D warnings'`

## Troubleshooting

### Build Issues

1. **Permission Denied**: Ensure Docker daemon is running and you have proper permissions
2. **Network Issues**: Verify internet connectivity for downloading Rust and Verus

### Runtime Issues

1. **Verification Failures**: Check the Verus output for specific error messages
2. **Memory Issues**: For large projects, you may need to increase Docker's memory allocation
3. **File Access**: When using volume mounts, ensure proper file permissions between host and container
4. **Path Issues**: Make sure your project directory contains a `Cargo.toml` file

### Common Commands

```bash
# Check Rust version inside container
docker run --rm verus-verifier rustc --version

# Check Verus version inside container
docker run --rm verus-verifier cargo verus --version

# List your project contents
docker run --rm -v /path/to/your/verus-project:/workspace verus-verifier ls -la

# Check if Cargo.toml exists
docker run --rm -v /path/to/your/verus-project:/workspace verus-verifier ls -la Cargo.toml
```

## Development Workflow

1. **Build the image** once: `docker build -f Dockerfile.verus -t verus-verifier .`
2. **Mount your project** and run verification: `docker run --rm -v /path/to/project:/workspace verus-verifier`
3. **Use interactive mode** for debugging: `docker run --rm -it -v /path/to/project:/workspace verus-verifier bash`
4. **Iterate rapidly** - changes to your local files are immediately reflected in the container

## Benefits of Volume Mounting

- **Live editing**: Changes to your local files are immediately available in the container
- **No rebuilding**: No need to rebuild the Docker image when you change your code
- **Faster iteration**: Start verification instantly without copying files
- **Consistent environment**: Same Verus and Rust versions every time
- **Easy debugging**: Use interactive mode to explore and debug issues

## Examples

```bash
# For your curve25519-dalek project
docker run --rm -v /home/lacra/git_repos/baif/temp/curve25519-dalek/:/workspace -w /workspace/curve25519-dalek verus-verifier

# Interactive debugging
docker run --rm -it -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace -w /workspace/curve25519-dalek verus-verifier bash

# Custom verification with flags
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace -w /workspace/curve25519-dalek verus-verifier cargo verus verify --verbose
```

## Notes

- The container automatically downloads the latest Verus release during build
- All verification output will be displayed in the terminal
- The container is designed to be stateless and can be safely removed after each run

# Verus Module Verification in Docker

## Issue Summary

When running Verus verification in a Docker container for a specific module in a Rust workspace project, you may encounter an error where the module cannot be found, even though it works locally.

## Problem

The command:
```bash
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier-prerelease \
  /usr/local/bin/verify-verus.sh --work-dir /workspace/curve25519-dalek \
  --verify-only-module backend::serial::u64::field_verus
```

Results in:
```
error: could not find module backend::serial::u64::field_verus specified by --verify-module or --verify-only-module
```

## Root Cause

The issue appears to be related to how Verus resolves modules when running in a Docker container with mounted volumes. When Verus is invoked from a workspace context, it may have difficulty locating modules in sub-crates.

## Solutions

### Solution 1: Run without module filtering first

First, verify that the Docker container can build and verify the entire project:

```bash
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier-prerelease \
  bash -c "cd /workspace/curve25519-dalek && cargo verus verify"
```

### Solution 2: Use the updated verify-verus.sh script

The updated script includes better debugging and workspace handling. Make sure your verify-verus.sh includes:

1. Workspace detection
2. Proper CARGO_TARGET_DIR setting
3. Debug output to help diagnose issues

### Solution 3: Alternative Docker command

If the issue persists, you can bypass the wrapper script and run the command directly:

```bash
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier-prerelease \
  bash -c "cd /workspace/curve25519-dalek && cargo verus verify -- --verify-only-module backend::serial::u64::field_verus"
```

### Solution 4: Build the project first

Sometimes Verus needs the project to be built before it can resolve modules:

```bash
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier-prerelease \
  bash -c "cd /workspace/curve25519-dalek && cargo build && cargo verus verify -- --verify-only-module backend::serial::u64::field_verus"
```

## Debugging Steps

If you continue to have issues:

1. Check that the module path is correct:
   ```bash
   find /home/lacra/git_repos/baif/curve25519-dalek -name "field_verus.rs"
   ```

2. Verify the module is properly declared in the parent module:
   ```bash
   grep "mod field_verus" /home/lacra/git_repos/baif/curve25519-dalek/curve25519-dalek/src/backend/serial/u64/mod.rs
   ```

3. Run with increased verbosity:
   ```bash
   docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier-prerelease \
     bash -c "cd /workspace/curve25519-dalek && RUST_LOG=debug cargo verus verify -- --verify-only-module backend::serial::u64::field_verus"
   ```

## Notes

- The issue seems specific to workspace projects where the actual crate is in a subdirectory
- Local execution works because it may have different environment setup or cached build artifacts
- The Docker container starts with a clean environment which may expose path resolution issues

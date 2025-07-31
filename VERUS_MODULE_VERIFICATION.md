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

The issue occurs because Verus needs the project to be built before it can properly resolve modules in the crate. When running in a fresh Docker container without any cached build artifacts, Verus cannot find the module structure without first compiling the project.

## Solution

The issue has been resolved by updating the `verify-verus.sh` script to run `cargo build` before `cargo verus verify`. This ensures that the project is compiled and all module structures are available for Verus to resolve.

The updated script now:
1. Runs `cargo build` (with package selection if specified)
2. Then runs `cargo verus verify` with the module filter

With this fix, the original command now works correctly:

```bash
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier-prerelease \
  /usr/local/bin/verify-verus.sh --work-dir /workspace/curve25519-dalek \
  --verify-only-module backend::serial::u64::field_verus
```

## Alternative Solutions (if needed)

### Manual build step

If you're using an older version of the script, you can manually add the build step:

```bash
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier-prerelease \
  bash -c "cd /workspace/curve25519-dalek && cargo build && cargo verus verify -- --verify-only-module backend::serial::u64::field_verus"
```

### For workspace projects with packages

If you need to specify a particular package in a workspace:

```bash
docker run --rm -v /home/lacra/git_repos/baif/curve25519-dalek:/workspace verus-verifier-prerelease \
  /usr/local/bin/verify-verus.sh --work-dir /workspace --package curve25519-dalek \
  --verify-only-module backend::serial::u64::field_verus
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

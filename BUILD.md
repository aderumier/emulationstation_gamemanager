# GameManager Build System

This document explains how to build and release GameManager packages.

## Quick Start

### Build Debian Package
```bash
# Simple build (syncs latest files automatically)
./build_deb.sh

# Or using Make
make build
```

### Full Release Process
```bash
# Interactive release with version bump, git operations, and Docker build
./build_release.sh

# Or using Make
make release
```

## Build Scripts

### `build_deb.sh`
- **Purpose**: Builds a Debian package with the latest source files
- **Features**:
  - Automatically syncs all source files to the Debian package directory
  - Verifies critical files contain expected updates
  - Cleans previous builds
  - Shows package information and contents
- **Usage**: `./build_deb.sh`

### `build_release.sh`
- **Purpose**: Full release process with version management
- **Features**:
  - Interactive version bumping
  - Git commit and tagging
  - Docker image building and pushing
  - Comprehensive error checking
- **Usage**: `./build_release.sh`

### `Makefile`
- **Purpose**: Convenient shortcuts for common operations
- **Available targets**:
  - `make build` - Build Debian package
  - `make clean` - Clean build artifacts
  - `make test` - Run basic syntax tests
  - `make install` - Build and install package
  - `make docker-build` - Build Docker image
  - `make docker-push` - Push Docker image
  - `make release` - Full release process

## Why This System?

### The Problem
Previously, the Debian package build process had a critical flaw:
- The `debian/opt/gamemanager/` directory contained **stale files** from previous builds
- When we made code changes, the Debian package would still contain the old code
- This led to bugs in production that were already fixed in development

### The Solution
The new build system ensures:
1. **Always Fresh**: Every build syncs the latest source files
2. **Verification**: Critical files are checked to ensure updates are included
3. **Automation**: Reduces human error in the build process
4. **Consistency**: Same process for development and release builds

## File Sync Process

The build script automatically syncs these files:
- `app.py` → `debian/opt/gamemanager/app.py`
- `box_generator.py` → `debian/opt/gamemanager/box_generator.py`
- `download_manager.py` → `debian/opt/gamemanager/download_manager.py`
- `static/` → `debian/opt/gamemanager/static/`
- `templates/` → `debian/opt/gamemanager/templates/`
- `var/config/` → `debian/opt/gamemanager/var/config/`
- Documentation files

## Verification

The build script verifies that critical updates are included:
- Checks for `get_launchbox_metadata_path` function
- Verifies directory creation logic is present
- Ensures no old constant usage remains

## Best Practices

1. **Always use the build scripts** instead of manual `dpkg-deb` commands
2. **Test the package** after building: `sudo dpkg -i gamemanager_*.deb`
3. **Use `make release`** for production releases
4. **Use `make build`** for development testing

## Troubleshooting

### Build Fails with "Critical files not found"
- Ensure you're in the project root directory
- Check that `app.py` contains the expected functions
- Run `make test` to verify syntax

### Package Installation Fails
- Check for dependency issues: `sudo apt-get install -f`
- Verify package integrity: `dpkg-deb --info gamemanager_*.deb`

### Docker Build Fails
- Ensure Docker is running
- Check that the Debian package was built successfully first
- Verify Docker Hub credentials for pushing

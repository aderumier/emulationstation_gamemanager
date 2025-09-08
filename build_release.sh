#!/bin/bash

# GameManager Release Builder
# This script handles version updates, git operations, and package building

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    print_error "Not in a git repository!"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    print_warning "You have uncommitted changes. Please commit or stash them first."
    git status --short
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get current version
CURRENT_VERSION=$(grep "^Version:" debian/DEBIAN/control | cut -d' ' -f2)
print_status "Current version: $CURRENT_VERSION"

# Ask for new version
read -p "Enter new version (current: $CURRENT_VERSION): " NEW_VERSION

if [ -z "$NEW_VERSION" ]; then
    NEW_VERSION="$CURRENT_VERSION"
fi

# Update version in control file
if [ "$NEW_VERSION" != "$CURRENT_VERSION" ]; then
    print_status "Updating version to $NEW_VERSION..."
    sed -i "s/^Version: .*/Version: $NEW_VERSION/" debian/DEBIAN/control
    print_success "Version updated in debian/DEBIAN/control"
fi

# Build the package
print_status "Building Debian package..."
./build_deb.sh

if [ $? -ne 0 ]; then
    print_error "Package build failed!"
    exit 1
fi

PACKAGE_NAME="gamemanager_${NEW_VERSION}_all.deb"

# Ask about git operations
read -p "Commit changes and create git tag? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Commit changes
    print_status "Committing changes..."
    git add .
    git commit -m "Release version $NEW_VERSION
    
    - Fixed directory creation for LaunchBox metadata
    - Enhanced debugging for metadata operations
    - Improved Debian package build process"
    
    # Create git tag
    print_status "Creating git tag v$NEW_VERSION..."
    git tag "v$NEW_VERSION"
    
    print_success "Git operations completed"
fi

# Ask about Docker build
read -p "Build Docker image? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Building Docker image..."
    
    # Update Dockerfile with new package name
    sed -i "s/COPY gamemanager_.*\.deb/COPY $PACKAGE_NAME/" Dockerfile
    sed -i "s/dpkg-deb -x gamemanager_.*\.deb/dpkg-deb -x $PACKAGE_NAME/" Dockerfile
    sed -i "s/LABEL version=\".*\"/LABEL version=\"$NEW_VERSION\"/" Dockerfile
    
    # Build Docker image
    docker build -t aderumier/emulationstation_gamemanager:$NEW_VERSION .
    docker build -t aderumier/emulationstation_gamemanager:latest .
    
    print_success "Docker image built successfully"
    
    # Ask about Docker Hub push
    read -p "Push to Docker Hub? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Pushing to Docker Hub..."
        docker push aderumier/emulationstation_gamemanager:$NEW_VERSION
        docker push aderumier/emulationstation_gamemanager:latest
        print_success "Docker images pushed to Docker Hub"
    fi
fi

print_success "Release build completed!"
print_status "Package: $PACKAGE_NAME"
print_status "Version: $NEW_VERSION"

if [ "$NEW_VERSION" != "$CURRENT_VERSION" ]; then
    print_status "Next steps:"
    echo "  1. Test the package: sudo dpkg -i $PACKAGE_NAME"
    echo "  2. Push to GitHub: git push origin main --tags"
    echo "  3. Create GitHub release with the package"
fi

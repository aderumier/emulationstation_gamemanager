#!/bin/bash

# GameManager Docker Publishing Script
# This script helps publish the GameManager Docker image to DockerHub

set -e

# Configuration
IMAGE_NAME="emulationstation_gamemanager"
DOCKERHUB_USERNAME="aderumier"
FULL_IMAGE_NAME="${DOCKERHUB_USERNAME}/${IMAGE_NAME}"

# Get version from git tag (like build_deb.sh)
if git describe --tags --exact-match HEAD >/dev/null 2>&1; then
    # We're on a tag, use it as version
    GIT_TAG=$(git describe --tags --exact-match HEAD)
    # Remove 'v' prefix if present for version
    VERSION=${GIT_TAG#v}
    echo "🏷️  Using git tag: $GIT_TAG -> version: $VERSION"
else
    # Not on a tag, use the last git tag
    LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null)
    if [ -n "$LAST_TAG" ]; then
        # Remove 'v' prefix if present for version
        VERSION=${LAST_TAG#v}
        echo "🏷️  Not on a tag, using last git tag: $LAST_TAG -> version: $VERSION"
    else
        echo "❌ Error: No git tags found. Cannot determine version."
        exit 1
    fi
fi

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

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running or not accessible"
        print_status "Please start Docker and try again"
        exit 1
    fi
    print_success "Docker is running"
}

# Function to get DockerHub username
get_dockerhub_username() {
    if [ -z "$DOCKERHUB_USERNAME" ]; then
        echo -n "Enter your DockerHub username: "
        read DOCKERHUB_USERNAME
        if [ -z "$DOCKERHUB_USERNAME" ]; then
            print_error "DockerHub username is required"
            exit 1
        fi
    fi
}

# Function to login to DockerHub
dockerhub_login() {
    print_status "Logging into DockerHub..."
    if docker login; then
        print_success "Successfully logged into DockerHub"
    else
        print_error "Failed to login to DockerHub"
        exit 1
    fi
}

# Function to build the image
build_image() {
    # Ensure username is set for build
    if [ -z "$DOCKERHUB_USERNAME" ]; then
        get_dockerhub_username
    fi
    FULL_IMAGE_NAME="${DOCKERHUB_USERNAME}/${IMAGE_NAME}"
    print_status "Building Docker image: ${FULL_IMAGE_NAME}:${VERSION}"
    # Determine the .deb file name based on version
    DEB_FILE="gamemanager_${VERSION}-1_all.deb"
    print_status "Using .deb package: ${DEB_FILE}"
    if docker build --build-arg DEB_FILE=${DEB_FILE} -t ${FULL_IMAGE_NAME}:${VERSION} .; then
        print_success "Image built successfully"
        # Also tag as latest during build
        docker tag ${FULL_IMAGE_NAME}:${VERSION} ${FULL_IMAGE_NAME}:latest
        print_status "Tagged as ${FULL_IMAGE_NAME}:latest"
    else
        print_error "Failed to build image"
        exit 1
    fi
}

# Function to tag images
tag_images() {
    print_status "Tagging images..."
    FULL_IMAGE_NAME="${DOCKERHUB_USERNAME}/${IMAGE_NAME}"
    
    # Tag latest (versioned tag already exists from build)
    docker tag ${FULL_IMAGE_NAME}:${VERSION} ${FULL_IMAGE_NAME}:latest
    
    print_success "Images tagged successfully"
}

# Function to push images
push_images() {
    print_status "Pushing images to DockerHub..."
    FULL_IMAGE_NAME="${DOCKERHUB_USERNAME}/${IMAGE_NAME}"
    
    # Push versioned image
    print_status "Pushing ${FULL_IMAGE_NAME}:${VERSION}..."
    if docker push ${FULL_IMAGE_NAME}:${VERSION}; then
        print_success "Versioned image pushed successfully"
    else
        print_error "Failed to push versioned image"
        exit 1
    fi
    
    # Push latest image
    print_status "Pushing ${FULL_IMAGE_NAME}:latest..."
    if docker push ${FULL_IMAGE_NAME}:latest; then
        print_success "Latest image pushed successfully"
    else
        print_error "Failed to push latest image"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -u, --username USERNAME    DockerHub username"
    echo "  -v, --version VERSION      Image version (default: 1.6-1)"
    echo "  -b, --build-only          Only build the image, don't push"
    echo "  -p, --push-only           Only push existing images, don't build"
    echo "  -c, --cleanup             Clean up old Docker images (keeps current version and latest)"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -u myusername                    # Build and push with username"
    echo "  $0 -u myusername -v 1.7.0          # Build and push specific version"
    echo "  $0 -u myusername -b                 # Only build, don't push"
    echo "  $0 -u myusername -p                 # Only push existing images"
}

# Function to clean up old local images
cleanup_old_images() {
    print_status "Cleaning up old Docker images..."
    
    # Ensure username is set
    if [ -z "$DOCKERHUB_USERNAME" ]; then
        get_dockerhub_username
    fi
    FULL_IMAGE_NAME="${DOCKERHUB_USERNAME}/${IMAGE_NAME}"
    
    # Get all images for this repository
    local all_images=$(docker images ${FULL_IMAGE_NAME} --format "{{.Repository}}:{{.Tag}}" 2>/dev/null || true)
    
    if [ -z "$all_images" ]; then
        print_status "No images found to clean up"
        return
    fi
    
    local cleaned_count=0
    while IFS= read -r image_tag; do
        # Skip current version and latest
        if [[ "$image_tag" != "${FULL_IMAGE_NAME}:${VERSION}" ]] && [[ "$image_tag" != "${FULL_IMAGE_NAME}:latest" ]]; then
            print_status "Removing old image: $image_tag"
            docker rmi "$image_tag" 2>/dev/null && ((cleaned_count++)) || true
        fi
    done <<< "$all_images"
    
    if [ $cleaned_count -gt 0 ]; then
        print_success "Cleaned up $cleaned_count old image(s)"
    else
        print_status "No old images to clean up"
    fi
}

# Parse command line arguments
BUILD_ONLY=false
PUSH_ONLY=false
CLEANUP_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--username)
            DOCKERHUB_USERNAME="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -b|--build-only)
            BUILD_ONLY=true
            shift
            ;;
        -p|--push-only)
            PUSH_ONLY=true
            shift
            ;;
        -c|--cleanup)
            CLEANUP_ONLY=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_status "GameManager Docker Publishing Script"
    print_status "Version: ${VERSION}"
    echo ""
    
    # Check Docker
    check_docker
    
    # Handle cleanup-only mode
    if [ "$CLEANUP_ONLY" = true ]; then
        cleanup_old_images
        exit 0
    fi
    
    if [ "$PUSH_ONLY" = false ]; then
        # Build image
        build_image
    fi
    
    if [ "$BUILD_ONLY" = false ]; then
        # Get DockerHub username
        get_dockerhub_username
        
        # Login to DockerHub
        dockerhub_login
        
        # Tag images
        tag_images
        
        # Push images
        push_images
        
        # Clean up old local images after successful push
        cleanup_old_images
        
        FULL_IMAGE_NAME="${DOCKERHUB_USERNAME}/${IMAGE_NAME}"
        print_success "All done! Your images are now available on DockerHub:"
        print_status "  ${FULL_IMAGE_NAME}:${VERSION}"
        print_status "  ${FULL_IMAGE_NAME}:latest"
        echo ""
        print_status "Users can now pull your image with:"
        print_status "  docker pull ${FULL_IMAGE_NAME}:latest"
    else
        if [ -z "$DOCKERHUB_USERNAME" ]; then
            get_dockerhub_username
        fi
        FULL_IMAGE_NAME="${DOCKERHUB_USERNAME}/${IMAGE_NAME}"
        print_success "Build completed. Image: ${FULL_IMAGE_NAME}:${VERSION}"
    fi
}

# Run main function
main "$@"



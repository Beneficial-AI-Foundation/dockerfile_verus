#!/bin/bash
# Verus Docker Image Installer

set -e

echo "🐳 Verus Docker Image Installer"
echo "================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Find the image file
IMAGE_FILE=""
for file in verus-docker-*.tar.gz; do
    if [[ "$file" != *"source"* ]] && [[ -f "$file" ]]; then
        IMAGE_FILE="$file"
        break
    fi
done

if [[ -z "$IMAGE_FILE" ]]; then
    echo "❌ No Docker image file found in current directory."
    echo "   Please download a verus-docker-*.tar.gz file from:"
    echo "   https://github.com/beneficial-ai-foundation/dockerfile_verus/releases"
    echo ""
    echo "   Available files:"
    echo "   • verus-docker-stable-vX.X.X.tar.gz (recommended)"
    echo "   • verus-docker-prerelease-vX.X.X.tar.gz"
    exit 1
fi

echo "📦 Found image: $IMAGE_FILE"
echo "🔄 Loading Docker image..."

# Load the image and capture the output
LOAD_OUTPUT=$(docker load < "$IMAGE_FILE" 2>&1)
echo "$LOAD_OUTPUT"

# Extract the loaded image name from the output
IMAGE_NAME=$(echo "$LOAD_OUTPUT" | grep "Loaded image:" | cut -d' ' -f3 | head -n1)

if [[ -z "$IMAGE_NAME" ]]; then
    echo "⚠️  Could not determine image name from load output."
    echo "   The image was loaded, but you may need to check 'docker images' to find it."
    IMAGE_NAME="<loaded-image-name>"
else
    echo "✅ Image loaded successfully: $IMAGE_NAME"
fi

echo ""
echo "🚀 Quick start examples:"
echo ""
echo "  # Verify entire project:"
echo "  docker run --rm -v /path/to/your/project:/workspace $IMAGE_NAME \\"
echo "    /usr/local/bin/verify-verus.sh --work-dir /workspace"
echo ""
echo "  # Verify specific module:"
echo "  docker run --rm -v /path/to/your/project:/workspace $IMAGE_NAME \\"
echo "    /usr/local/bin/verify-verus.sh --work-dir /workspace \\"
echo "    --verify-only-module module::path::name"
echo ""
echo "  # Generate JSON report:"
echo "  docker run --rm -v /path/to/your/project:/workspace $IMAGE_NAME \\"
echo "    /usr/local/bin/verify-verus.sh --work-dir /workspace \\"
echo "    --json-output /workspace/verification_report.json"
echo ""
echo "  # Interactive shell (for debugging):"
echo "  docker run --rm -it -v /path/to/your/project:/workspace $IMAGE_NAME bash"
echo ""
echo "📖 For complete documentation, see:"
echo "   https://github.com/beneficial-ai-foundation/dockerfile_verus/blob/master/README.md"
echo ""
echo "✨ Installation complete! Happy verifying!"

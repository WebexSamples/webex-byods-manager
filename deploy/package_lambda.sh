#!/bin/bash

# AWS Lambda Deployment Package Creator for Webex BYODS Manager
# This script creates a deployment package (ZIP file) for AWS Lambda

set -euo pipefail

echo "========================================="
echo "AWS Lambda Deployment Package Creator"
echo "========================================="
echo ""

# Configuration
PACKAGE_DIR="lambda_package"
OUTPUT_ZIP="lambda_deployment.zip"
PYTHON_VERSION="${PYTHON_VERSION:-3.14}"
LAMBDA_ARCHITECTURE="${LAMBDA_ARCHITECTURE:-x86_64}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

case "$LAMBDA_ARCHITECTURE" in
    x86_64)
        LAMBDA_PLATFORM="manylinux2014_x86_64"
        ;;
    arm64)
        LAMBDA_PLATFORM="manylinux2014_aarch64"
        ;;
    *)
        echo "Unsupported Lambda architecture: $LAMBDA_ARCHITECTURE"
        echo "Supported architectures: x86_64, arm64"
        exit 1
        ;;
esac

# Clean up any previous package directory
if [ -d "$PACKAGE_DIR" ]; then
    echo "Cleaning up previous package directory..."
    rm -rf "$PACKAGE_DIR"
fi

# Create fresh package directory
echo "Creating package directory..."
mkdir -p "$PACKAGE_DIR"

# Install dependencies
echo ""
echo "Installing Python dependencies..."
echo "Targeting Python $PYTHON_VERSION on $LAMBDA_ARCHITECTURE Linux"

# Check if we're in a virtual environment
if [ -z "${VIRTUAL_ENV:-}" ]; then
    echo "Warning: Not in a virtual environment. It's recommended to activate your venv first."
    echo "Continuing anyway..."
fi

# Resolve Linux wheels even when packaging from macOS or Windows. Native host
# wheels cannot be imported by the Lambda runtime.
"$PYTHON_BIN" -m pip install --target "$PACKAGE_DIR" \
    -r ../requirements.txt \
    --upgrade \
    --platform "$LAMBDA_PLATFORM" \
    --implementation cp \
    --python-version "$PYTHON_VERSION" \
    --only-binary=:all: \
    --no-compile \
    --quiet

echo "✓ Dependencies installed"

# Copy required Python files
echo ""
echo "Copying application files..."
cp ../lambda_function.py "$PACKAGE_DIR/"
cp ../token_manager.py "$PACKAGE_DIR/"

echo "✓ Application files copied"

# Create the deployment ZIP
echo ""
echo "Creating deployment package..."

# Remove old ZIP if it exists
if [ -f "$OUTPUT_ZIP" ]; then
    rm "$OUTPUT_ZIP"
fi

# Create ZIP from package directory
cd "$PACKAGE_DIR"
zip -r9 "../$OUTPUT_ZIP" . -q
cd ..

# Get ZIP file size
ZIP_SIZE=$(du -h "$OUTPUT_ZIP" | cut -f1)

echo "✓ Deployment package created: $OUTPUT_ZIP ($ZIP_SIZE)"

# Clean up package directory (optional - uncomment to keep it)
echo ""
echo "Cleaning up temporary files..."
rm -rf "$PACKAGE_DIR"
echo "✓ Cleanup complete"

echo ""
echo "========================================="
echo "Deployment package ready!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Upload $OUTPUT_ZIP to AWS Lambda"
echo "2. Set up AWS Secrets Manager with your credentials"
echo "3. Configure environment variables in Lambda"
echo "4. Set up EventBridge trigger for hourly execution"
echo ""
echo "For detailed instructions, see deploy/AWS_SETUP.md"
echo ""

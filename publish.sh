#!/usr/bin/env bash
set -e

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

REPOSITORY="pypi"
SKIP_TESTS=false
CONFIRM=true

usage() {
    echo -e "${BLUE}Usage:${NC} $0 [options]"
    echo ""
    echo "Options:"
    echo "  --test, --testpypi  Publish to TestPyPI instead of production PyPI"
    echo "  --skip-tests        Skip running pytest before building"
    echo "  -y, --yes           Skip confirmation prompt"
    echo "  -h, --help          Show this help message"
    echo ""
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --test|--testpypi)
            REPOSITORY="testpypi"
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -y|--yes)
            CONFIRM=false
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Determine execution prefix (uv or python3)
if command -v uv &> /dev/null; then
    RUN_CMD="uv run"
else
    RUN_CMD=""
fi

echo -e "${BLUE}=== Mello SDK Release Workflow ===${NC}"
echo -e "Target Repository: ${YELLOW}${REPOSITORY}${NC}"

# Step 1: Run Tests
if [ "$SKIP_TESTS" = false ]; then
    echo -e "\n${BLUE}[1/4] Running unit tests...${NC}"
    if [ -n "$RUN_CMD" ]; then
        $RUN_CMD pytest
    else
        pytest
    fi
else
    echo -e "\n${YELLOW}[1/4] Skipping unit tests...${NC}"
fi

# Step 2: Clean previous build artifacts
echo -e "\n${BLUE}[2/4] Cleaning build artifacts...${NC}"
rm -rf dist/ build/ *.egg-info

# Step 3: Build package
echo -e "\n${BLUE}[3/4] Building package...${NC}"
if [ -n "$RUN_CMD" ]; then
    $RUN_CMD python -m build
else
    python3 -m build
fi

# Check built artifacts
if [ -n "$RUN_CMD" ]; then
    $RUN_CMD python -m twine check dist/*
else
    python3 -m twine check dist/*
fi

# Step 4: Confirm and Upload
echo -e "\n${BLUE}[4/4] Uploading to ${YELLOW}${REPOSITORY}${BLUE}...${NC}"

if [ "$CONFIRM" = true ]; then
    read -p "Are you sure you want to publish dist/* to ${REPOSITORY}? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Publishing cancelled by user.${NC}"
        exit 0
    fi
fi

if [ "$REPOSITORY" = "testpypi" ]; then
    if [ -n "$RUN_CMD" ]; then
        $RUN_CMD python -m twine upload --repository testpypi dist/*
    else
        python3 -m twine upload --repository testpypi dist/*
    fi
else
    if [ -n "$RUN_CMD" ]; then
        $RUN_CMD python -m twine upload dist/*
    else
        python3 -m twine upload dist/*
    fi
fi

echo -e "\n${GREEN}=== Successfully published to ${REPOSITORY}! ===${NC}"

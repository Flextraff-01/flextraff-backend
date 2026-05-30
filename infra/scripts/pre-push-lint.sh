#!/bin/bash
# Pre-push linting script for FlexTraff Backend
# Run this before pushing to any branch to ensure code quality

set -e  # Exit on any error

echo "🔍 Running pre-push linting checks..."

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
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a git repository!"
    exit 1
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    print_error "Python is not installed or not in PATH!"
    exit 1
fi

print_status "Checking Python version..."
python_version=$(python --version 2>&1 | cut -d' ' -f2)
print_status "Using Python $python_version"

# Install required linting tools if not available
print_status "Ensuring linting tools are available..."
pip install flake8 bandit --quiet

# Run Flake8 linting
print_status "Running Flake8 linting..."
if flake8 app/ tests/ main.py --statistics; then
    print_success "Flake8 linting passed!"
else
    print_error "Flake8 linting failed! Please fix the issues before pushing."
    exit 1
fi

# Run Bandit security check
print_status "Running Bandit security scan..."
if bandit -r app/ -f json > /dev/null 2>&1; then
    print_success "Security scan passed!"
else
    print_warning "Security scan found potential issues. Review them carefully."
    bandit -r app/ -ll
fi

# Check for common issues
print_status "Checking for common issues..."

# Check for debug statements
if grep -r "pdb.set_trace()" app/ tests/ main.py 2>/dev/null; then
    print_error "Found debug statements (pdb.set_trace)! Remove them before pushing."
    exit 1
fi

# Check for print statements (basic check)
if grep -r "print(" app/ 2>/dev/null | grep -v "# Allow print" | head -5; then
    print_warning "Found print statements in app/. Consider using logging instead."
fi

# Check for TODO/FIXME comments
todo_count=$(grep -r "TODO\|FIXME" app/ tests/ main.py 2>/dev/null | wc -l)
if [ "$todo_count" -gt 0 ]; then
    print_warning "Found $todo_count TODO/FIXME comments. Review if any are critical."
fi

print_success "🎉 All linting checks passed!"
print_status "Your code is ready to push to any branch."

echo ""
echo "📋 Summary:"
echo "✅ Flake8 linting: PASSED"
echo "✅ Security scan: CHECKED"
echo "✅ Common issues: CHECKED"
echo ""
echo "💡 Tip: You can run 'pre-commit install' to automatically run these checks before each commit."
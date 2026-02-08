#!/usr/bin/env bash
# Getting Started - FSBO Scraper V2
# This script demonstrates the basic workflow

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              FSBO Scraper V2 - Getting Started                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python installation
echo "✓ Checking Python installation..."
python --version || python3 --version
echo ""

# Determine python command
if command -v python3 &> /dev/null; then
    PYTHON=python3
else
    PYTHON=python
fi

echo "Using: $PYTHON"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
$PYTHON -m pip install --upgrade pip > /dev/null 2>&1
$PYTHON -m pip install -r requirements.txt > /dev/null 2>&1
echo "✓ Dependencies installed"
echo ""

# Install playwright browsers
echo "🌐 Installing Playwright browsers..."
$PYTHON -m playwright install > /dev/null 2>&1
echo "✓ Browsers installed"
echo ""

# Initialize project
echo "⚙️  Initializing project..."
$PYTHON main.py init
echo ""

# Show configuration
echo "📋 Current Configuration:"
$PYTHON main.py config
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                   Setup Complete!                              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. Run your first scrape:"
echo "   $ python main.py scrape"
echo ""
echo "2. View the results:"
echo "   $ python main.py list --limit 10"
echo ""
echo "3. Export to CSV:"
echo "   $ python main.py export -o listings.csv"
echo ""
echo "4. View statistics:"
echo "   $ python main.py stats"
echo ""
echo "For more information:"
echo "   - README.md - Full documentation"
echo "   - SETUP.md - Detailed setup instructions"
echo "   - QUICK_REFERENCE.md - Common commands"
echo ""

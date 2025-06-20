#!/bin/bash

# Eva Assistant V1 - Installation Script with uv
# This script sets up the Eva Assistant project using uv

echo "🚀 Setting up Eva Assistant V1..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ uv installed successfully!"
    echo "⚠️  Please restart your terminal or run: source ~/.bashrc"
    echo "⚠️  Then run this script again."
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+' | head -1)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
uv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing main dependencies..."
uv pip install -r requirements.txt

# Ask if they want dev dependencies
read -p "📋 Install development dependencies? (y/N): " install_dev
if [[ $install_dev =~ ^[Yy]$ ]]; then
    echo "📥 Installing development dependencies..."
    uv pip install -r requirements-dev.txt
    echo "✅ Development dependencies installed!"
fi

# Copy environment template
if [ ! -f .env ]; then
    echo "📄 Creating .env file from template..."
    cp env.example .env
    echo "✅ .env file created!"
    echo "⚠️  Please edit .env with your OAuth credentials"
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
mkdir -p data oauth/tokens

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your OAuth credentials"
echo "2. Run: python scripts/setup_oauth.py --all"
echo "3. Start developing Eva Assistant!"
echo ""
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To run OAuth setup:"
echo "  python scripts/setup_oauth.py --all" 
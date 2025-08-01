#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Setting up Albert Python SDK dev environment..."

# Install uv via pip
echo "🌀 Installing uv via pip..."
pip install uv pre-commit

# Install project + dev dependencies
echo "📦 Installing project & dev dependencies with uv..."
uv sync

# Install pre-commit hooks
echo "🔧 Installing/updating pre-commit hooks..."
pre-commit install --install-hooks

echo ""
echo "✅ Setup complete!"
echo "   • To refresh pre-commit hooks later:  pre-commit install --install-hooks"

#!/bin/bash

# Script to set up git hooks for the project

echo "🔧 Setting up git hooks for Kasa Monitor..."

# Configure git to use our hooks directory
git config core.hooksPath .githooks

if [ $? -eq 0 ]; then
    echo "✅ Git hooks configured successfully!"
    echo ""
    echo "The prepare-commit-msg hook will now:"
    echo "  • Detect source code changes in your commits"
    echo "  • Remind you to add [docker-build] tag when needed"
    echo "  • Help ensure Docker images are built for code changes"
    echo ""
    echo "To disable hooks: git config --unset core.hooksPath"
else
    echo "❌ Failed to configure git hooks"
    exit 1
fi
#!/bin/bash

# OpenClaw VM Platform - Backend Development Setup Script
# This script sets up the development environment

set -e

echo "🚀 OpenClaw VM Platform - Backend Setup"
echo "========================================"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $PYTHON_VERSION"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs

# Run database migrations (if database is available)
echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your database and Redis configuration"
echo "2. Start PostgreSQL and Redis: docker-compose up -d postgres redis"
echo "3. Run database migrations: alembic upgrade head"
echo "4. Seed initial data: python -m app.seed_data"
echo "5. Start development server: uvicorn app.main:app --reload"
echo ""
echo "API will be available at: http://localhost:8000"
echo "Documentation: http://localhost:8000/api/docs"

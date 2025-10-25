#!/bin/bash
# Deployment script for SLR Automation App

echo "🚀 Starting deployment process..."

# Check if we're using the deployment requirements
if [ -f "requirements-deploy.txt" ]; then
    echo "📦 Installing deployment-optimized requirements..."
    pip install -r requirements-deploy.txt
else
    echo "📦 Installing standard requirements..."
    pip install -r requirements.txt
fi

echo "✅ Dependencies installed successfully!"
echo "🌐 Starting application..."

# Start the application
gunicorn server:app --bind 0.0.0.0:$PORT

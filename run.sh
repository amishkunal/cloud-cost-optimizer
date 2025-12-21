#!/bin/bash

# Cloud Cost Optimizer - Quick Start Script
# This script sets up and runs the entire project

set -e  # Exit on error

PROJECT_DIR="/Users/amish.kunal/cloud-cost-optimizer"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "=========================================="
echo "🚀 Cloud Cost Optimizer - Quick Start"
echo "=========================================="
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is required but not installed. Aborting."; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js is required but not installed. Aborting."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting."; exit 1; }
echo "✅ All prerequisites met"
echo ""

# Step 1: Start Database
echo "=========================================="
echo "📦 Step 1: Starting Database Services"
echo "=========================================="
cd "$PROJECT_DIR"
docker-compose up -d
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5
echo "✅ Database services started"
echo ""

# Step 2: Setup Backend
echo "=========================================="
echo "🐍 Step 2: Setting Up Backend"
echo "=========================================="
cd "$BACKEND_DIR"

# Install Python dependencies
if [ ! -d "venv" ] && [ ! -d ".venv" ]; then
    echo "📦 Installing Python dependencies..."
    pip3 install -r requirements.txt
else
    echo "📦 Python dependencies already installed (venv detected)"
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating template..."
    cat > .env << EOF
# Database Configuration (matches docker-compose.yml)
DB_HOST=localhost
DB_PORT=5432
DB_USER=ccopt
DB_PASSWORD=ccoptpassword
DB_NAME=ccopt_db

# OpenAI API Key (optional, for LLM explanations)
OPENAI_API_KEY=

# AWS Credentials (optional, for CloudWatch ingestion)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-west-2
AWS_INSTANCE_IDS=
EOF
    echo "✅ Created .env file. Edit it to add your API keys if needed."
else
    echo "✅ .env file exists"
fi

# Initialize database and seed data
echo "🗄️  Initializing database..."
python3 -c "from app.db import Base, engine; Base.metadata.create_all(bind=engine)" 2>/dev/null || echo "Database tables already exist"

# Check if data exists
INSTANCE_COUNT=$(python3 -c "from app.db import SessionLocal; from app.models import Instance; db = SessionLocal(); print(len(db.query(Instance).all())); db.close()" 2>/dev/null || echo "0")

if [ "$INSTANCE_COUNT" = "0" ]; then
    echo "📊 Seeding demo data..."
    python3 -m app.ingestion.synthetic_ingest
else
    echo "✅ Database already has data ($INSTANCE_COUNT instances)"
fi

# Check if model exists
if [ ! -f "app/ml_models/xgb_downsize_classifier.joblib" ]; then
    echo "🤖 Training ML model..."
    python3 -m app.ml.train_model
else
    echo "✅ ML model already exists"
fi

echo "✅ Backend setup complete"
echo ""

# Step 3: Setup Frontend
echo "=========================================="
echo "⚛️  Step 3: Setting Up Frontend"
echo "=========================================="
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
else
    echo "✅ Node.js dependencies already installed"
fi

echo "✅ Frontend setup complete"
echo ""

# Step 4: Start Services
echo "=========================================="
echo "🎯 Step 4: Starting Services"
echo "=========================================="
echo ""
echo "Starting services in separate terminals..."
echo ""

# Start backend in background (or new terminal)
echo "📡 Starting backend server..."
cd "$BACKEND_DIR"
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"
echo "   Logs: $BACKEND_DIR/backend.log"
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
sleep 3

# Test backend
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is responding"
else
    echo "⚠️  Backend may not be ready yet. Check logs: $BACKEND_DIR/backend.log"
fi
echo ""

# Start frontend
echo "🌐 Starting frontend server..."
cd "$FRONTEND_DIR"
nohup npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"
echo "   Logs: $FRONTEND_DIR/frontend.log"
echo "   UI: http://localhost:3000"
echo ""

# Wait for frontend to be ready
echo "⏳ Waiting for frontend to be ready..."
sleep 5

echo ""
echo "=========================================="
echo "✅ All Services Running!"
echo "=========================================="
echo ""
echo "📍 Access Points:"
echo "   Frontend UI:  http://localhost:3000"
echo "   Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo ""
echo "📊 Process IDs:"
echo "   Backend:  $BACKEND_PID"
echo "   Frontend: $FRONTEND_PID"
echo ""
echo "📝 Logs:"
echo "   Backend:  $BACKEND_DIR/backend.log"
echo "   Frontend: $FRONTEND_DIR/frontend.log"
echo ""
echo "🛑 To stop all services:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   docker-compose down"
echo ""
echo "🎉 Open http://localhost:3000 in your browser!"
echo ""


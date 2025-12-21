# How to Run Cloud Cost Optimizer

Complete setup and run instructions for the Cloud Cost Optimizer project.

## Prerequisites

- **Python 3.12+** - [Download here](https://www.python.org/downloads/)
- **Node.js 20+** - [Download here](https://nodejs.org/)
- **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop/)
- **Git** - Usually pre-installed

## Quick Start (Automated)

The easiest way to get started:

```bash
cd /Users/amish.kunal/cloud-cost-optimizer
chmod +x run.sh
./run.sh
```

This script will:
- ✅ Start Docker containers (PostgreSQL, Redis)
- ✅ Install all dependencies
- ✅ Seed demo data
- ✅ Train the ML model
- ✅ Start backend and frontend servers

Then open **http://localhost:3000** in your browser.

---

## Manual Setup (Step-by-Step)

### Step 1: Start Database

Open a terminal and run:

```bash
cd /Users/amish.kunal/cloud-cost-optimizer
docker-compose up -d
```

This starts:
- PostgreSQL database on port 5432
- Redis on port 6379

**Verify it's running:**
```bash
docker ps
```

You should see `ccopt_postgres` and `ccopt_redis` containers.

---

### Step 2: Setup Backend

Open a **new terminal**:

```bash
cd /Users/amish.kunal/cloud-cost-optimizer/backend
```

#### 2.1 Install Python Dependencies

```bash
pip3 install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, XGBoost, and other dependencies.

#### 2.2 Create Environment File

Create `backend/.env` file (optional, for API keys):

```bash
cat > .env << 'EOF'
# Database (matches docker-compose.yml - already configured)
DB_HOST=localhost
DB_PORT=5432
DB_USER=ccopt
DB_PASSWORD=ccoptpassword
DB_NAME=ccopt_db

# Optional: OpenAI API Key (for LLM explanations)
OPENAI_API_KEY=your_openai_api_key_here

# Optional: AWS Credentials (for CloudWatch ingestion)
AWS_ACCESS_KEY_ID=your_aws_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_here
AWS_REGION=us-west-2
AWS_INSTANCE_IDS=i-0123456789abcdef0
EOF
```

#### 2.3 Initialize Database and Seed Data

```bash
# Create database tables
python3 -c "from app.db import Base, engine; Base.metadata.create_all(bind=engine)"

# Seed demo data (creates 25 instances with 7 days of metrics)
python3 -m app.ingestion.synthetic_ingest

# Train the ML model
python3 -m app.ml.train_model
```

You should see:
```
✅ Seeded 25 instances
✅ Inserted 4200 metrics
✅ Model trained successfully
```

#### 2.4 Start Backend Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Keep this terminal open!** The server runs with auto-reload enabled.

**Test the backend:**
```bash
curl http://localhost:8000/health
```

Should return: `{"status":"ok"}`

---

### Step 3: Setup Frontend

Open a **new terminal**:

```bash
cd /Users/amish.kunal/cloud-cost-optimizer/frontend
```

#### 3.1 Install Node.js Dependencies

```bash
npm install
```

This installs Next.js, React, Chart.js, and other frontend dependencies.

#### 3.2 Start Frontend Server

```bash
npm run dev
```

You should see:
```
- Local:        http://localhost:3000
✓ Ready in Xs
```

**Keep this terminal open too!**

---

### Step 4: Access the Application

Open your browser and navigate to:

- **Frontend Dashboard**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

---

## Testing the Application

### Test Backend API

```bash
# Health check
curl http://localhost:8000/health

# Get recommendations
curl "http://localhost:8000/recommendations?min_savings=0"

# Get analytics
curl http://localhost:8000/analytics/summary
```

### Explore the Frontend

1. **Home Page** - Shows backend health status
2. **Instances** - View all cloud instances in a table
3. **Recommendations** - See ML-driven optimization suggestions
4. **Analytics** - View system-wide cost metrics and trends

---

## Refreshing Demo Data

To reset and regenerate demo data:

```bash
cd backend
python3 -m scripts.refresh_demo_data
```

This will:
- Clear existing data
- Reseed with fresh instances and metrics
- Retrain the ML model

---

## Stopping the Application

1. **Stop Frontend**: Press `Ctrl+C` in the frontend terminal
2. **Stop Backend**: Press `Ctrl+C` in the backend terminal
3. **Stop Database**:
   ```bash
   docker-compose down
   ```

---

## Troubleshooting

### Backend Won't Start

**Port 8000 already in use:**
```bash
lsof -i :8000
kill -9 <PID>
```

**Database connection error:**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Restart database
docker-compose restart db
```

**Missing dependencies:**
```bash
cd backend
pip3 install -r requirements.txt
```

### Frontend Won't Start

**Port 3000 already in use:**
```bash
lsof -i :3000
kill -9 <PID>
```

**Node modules issues:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### No Recommendations Showing

**Check if data exists:**
```bash
cd backend
python3 -c "from app.db import SessionLocal; from app.models import Instance; db = SessionLocal(); print(f'Instances: {len(db.query(Instance).all())}'); db.close()"
```

**Reseed data if needed:**
```bash
python3 -m scripts.refresh_demo_data
```

### Model Not Found Error

```bash
cd backend
python3 -m app.ml.train_model
```

---

## Optional: AWS CloudWatch Integration

To ingest real AWS EC2 metrics:

1. **Set AWS credentials** in `backend/.env`:
   ```env
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=us-west-2
   AWS_INSTANCE_IDS=i-0123456789abcdef0
   ```

2. **Run ingestion:**
   ```bash
   cd backend
   python3 -m app.ingestion.aws_cloudwatch_ingest
   ```

This will pull the last 24 hours of metrics from your EC2 instances.

---

## Project Structure

```
cloud-cost-optimizer/
├── backend/
│   ├── app/
│   │   ├── routers/        # API endpoints
│   │   ├── ml/             # ML training & inference
│   │   ├── ingestion/      # Data ingestion
│   │   └── llm/           # AI explanations
│   ├── scripts/           # Utility scripts
│   └── requirements.txt
├── frontend/
│   ├── src/app/           # Next.js pages
│   └── package.json
├── docker-compose.yml     # Database setup
└── run.sh                 # Quick start script
```

---

## Need Help?

- Check backend logs: Look at the terminal where `uvicorn` is running
- Check frontend logs: Look at the terminal where `npm run dev` is running
- Check database logs: `docker-compose logs db`
- API documentation: http://localhost:8000/docs

---

## All Set! 🎉

Your Cloud Cost Optimizer should now be running:
- ✅ Database on port 5432
- ✅ Backend API on port 8000
- ✅ Frontend UI on port 3000

Visit **http://localhost:3000** to start exploring!


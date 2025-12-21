# Cloud Cost Optimizer - Startup Instructions

Follow these steps to start the application from scratch.

## Prerequisites Checklist
- ✅ Python 3.12+ installed
- ✅ Node.js and npm installed
- ✅ Docker and Docker Compose installed
- ✅ OpenAI API key (optional, for LLM explanations)

---

## Step 1: Start Database Services

Open a terminal and run:

```bash
cd /Users/amish.kunal/cloud-cost-optimizer
docker-compose up -d
```

This starts:
- PostgreSQL database on port 5432
- Redis on port 6379

Verify they're running:
```bash
docker ps
```

You should see `ccopt_postgres` and `ccopt_redis` containers.

---

## Step 2: Set Up Backend Environment

In a new terminal:

```bash
cd /Users/amish.kunal/cloud-cost-optimizer/backend
```

### 2.1 Install Python Dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, XGBoost, OpenAI, and other dependencies.

### 2.2 Create/Verify .env File

Create `backend/.env` if it doesn't exist:

```bash
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
EOF
```

Replace `your_openai_api_key_here` with your actual OpenAI API key (optional, but needed for LLM explanations).

### 2.3 Initialize Database and Train Model

```bash
# Run database migrations (creates tables)
python -m app.db

# Ingest synthetic data (if needed)
python -m app.ingestion.synthetic_ingest

# Train the ML model
python -m app.ml.train_model
```

---

## Step 3: Start Backend Server

In the same backend terminal:

```bash
cd /Users/amish.kunal/cloud-cost-optimizer/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**Keep this terminal open!** The server runs in the foreground with auto-reload enabled.

Verify backend is running:
```bash
curl http://localhost:8000/health
```

Should return: `{"status":"ok"}`

---

## Step 4: Start Frontend Server

Open a **new terminal**:

```bash
cd /Users/amish.kunal/cloud-cost-optimizer/frontend
npm install
npm run dev
```

You should see:
```
- Local:        http://localhost:3000
✓ Ready in Xs
```

**Keep this terminal open too!**

---

## Step 5: Open the Application

Open your browser and navigate to:
- **Frontend**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs

---

## Quick Verification

Test these endpoints:

1. **Health Check:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Get Recommendations:**
   ```bash
   curl "http://localhost:8000/recommendations?min_savings=0"
   ```

3. **Get Analytics:**
   ```bash
   curl http://localhost:8000/analytics/summary
   ```

4. **LLM Explanation (if API key is set):**
   ```bash
   curl http://localhost:8000/recommendations/1/llm_explanation
   ```

---

## Troubleshooting

### Backend won't start
- Check if port 8000 is already in use: `lsof -i :8000`
- Verify database is running: `docker ps`
- Check Python dependencies: `pip list | grep fastapi`

### Frontend won't start
- Check if port 3000 is already in use: `lsof -i :3000`
- Verify Node modules are installed: `ls node_modules`
- Try: `rm -rf node_modules package-lock.json && npm install`

### Database connection errors
- Verify PostgreSQL is running: `docker ps | grep postgres`
- Check connection: `docker exec -it ccopt_postgres psql -U ccopt -d ccopt_db`

### Model not found error
- Run: `python -m app.ml.train_model`

### LLM explanations not working
- Verify API key in `backend/.env`
- Restart backend server after adding API key
- Check OpenAI package: `pip show openai`

---

## Stopping Everything

1. **Stop Frontend**: Press `Ctrl+C` in the frontend terminal
2. **Stop Backend**: Press `Ctrl+C` in the backend terminal
3. **Stop Database**: 
   ```bash
   docker-compose down
   ```

---

## All Set! 🎉

Your Cloud Cost Optimizer should now be running with:
- ✅ Database on port 5432
- ✅ Backend API on port 8000
- ✅ Frontend UI on port 3000

Visit http://localhost:3000 to see the application!






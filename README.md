# Cloud Cost Optimizer 

> AI-powered platform that automatically identifies cost-saving opportunities in cloud infrastructure using machine learning

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-orange.svg)](https://xgboost.readthedocs.io/)

## What It Does

Cloud Cost Optimizer helps organizations reduce cloud infrastructure spending by automatically analyzing server utilization and recommending which instances can be downsized. Instead of manually reviewing hundreds of servers, the platform uses machine learning to identify underutilized resources and estimates potential monthly savings.

**Key Features:**
- **ML-Powered Recommendations** - XGBoost model identifies instances that can be downsized
- **Real-Time Analytics** - Dashboard showing current costs vs. optimized costs
- **AWS Integration** - Pulls real metrics from AWS CloudWatch
- **AI Explanations** - GPT-powered explanations for each recommendation
- **Cost Trends** - Visualize projected savings over time

## How It Works

1. **Data Collection** - Ingests CPU, memory, and network metrics from cloud instances (AWS CloudWatch or synthetic data)
2. **Feature Engineering** - Aggregates metrics over time to understand utilization patterns
3. **ML Analysis** - Trained XGBoost model predicts which instances are underutilized
4. **Recommendations** - Provides actionable suggestions with projected monthly savings
5. **Visualization** - Interactive dashboard shows trends and potential cost reductions

## Tech Stack

**Backend:**
- FastAPI (Python) - REST API
- PostgreSQL - Time-series metrics storage
- XGBoost - Machine learning model
- SQLAlchemy - Database ORM

**Frontend:**
- Next.js 16 - React framework
- TypeScript - Type safety
- Chart.js - Data visualization
- Tailwind CSS - Styling

**ML & AI:**
- XGBoost - Classification model
- OpenAI API - Natural language explanations
- scikit-learn - Model evaluation

**Infrastructure:**
- Docker Compose - Database setup
- AWS CloudWatch - Real-time metrics (optional)


## Use Cases

- **FinOps Teams** - Track and optimize cloud spending
- **DevOps Engineers** - Identify underutilized infrastructure
- **Engineering Managers** - Make data-driven decisions about resource allocation
- **Startups** - Reduce cloud costs without manual analysis

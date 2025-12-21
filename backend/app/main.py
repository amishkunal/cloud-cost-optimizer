from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routers import analytics, cost_trends, health, instances, ml, recommendations


def create_app() -> FastAPI:
    app = FastAPI(title="Cloud Cost Optimizer API", version="0.1.0")

    # CORS: allow Next.js dev server
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",  # In case Next.js uses different port
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup():
        Base.metadata.create_all(bind=engine)

    app.include_router(health.router)
    app.include_router(instances.router)
    app.include_router(recommendations.router)
    app.include_router(cost_trends.router)
    app.include_router(analytics.router)
    app.include_router(ml.router)

    @app.get("/")
    async def root():
        return {"message": "Cloud Cost Optimizer API"}

    return app


app = create_app()

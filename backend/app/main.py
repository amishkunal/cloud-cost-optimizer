from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .metrics import METRICS, RequestTimer

from .routers import (
    actions,
    analytics,
    cost_trends,
    health,
    instances,
    metrics,
    ml,
    recommendations,
)


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

    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        # Skip /metrics to avoid self-scrape amplification.
        if request.url.path == "/metrics":
            return await call_next(request)

        timer = RequestTimer()
        response = await call_next(request)
        METRICS.observe_http(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=timer.elapsed_ms(),
        )
        return response

    @app.on_event("startup")
    def on_startup():
        Base.metadata.create_all(bind=engine)

    app.include_router(health.router)
    app.include_router(instances.router)
    app.include_router(actions.router)
    app.include_router(recommendations.router)
    app.include_router(cost_trends.router)
    app.include_router(analytics.router)
    app.include_router(metrics.router)
    app.include_router(ml.router)

    @app.get("/")
    async def root():
        return {"message": "Cloud Cost Optimizer API"}

    return app


app = create_app()

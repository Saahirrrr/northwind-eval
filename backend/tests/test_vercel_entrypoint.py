"""Regression checks for the Vercel FastAPI entrypoint."""

from app.main import app as application_app
from main import app as vercel_app


def test_vercel_entrypoint_imports_fastapi_app():
    assert vercel_app is application_app
    assert vercel_app.title == "Gridbricks Wind Intelligence"
    routes = {route.path for route in vercel_app.routes}

    assert {
        "/api/health",
        "/api/metadata",
        "/api/analysis/accuracy",
        "/api/analysis/vintages",
        "/api/analysis/provenance",
    } <= routes

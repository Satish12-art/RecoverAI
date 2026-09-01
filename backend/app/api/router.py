"""Main API router assembling all sub-routers for RecoverAI."""

from fastapi import APIRouter

from app.api.dashboard import router as dashboard_router
from app.api.payments import router as payments_router
from app.api.cases import router as cases_router
from app.api.analytics import router as analytics_router
from app.api.audit import router as audit_router
from app.api.simulate import router as simulate_router
from app.api.policy import router as policy_router
from app.api.agent import router as agent_router
from app.api.evaluation import router as evaluation_router
from app.api.webhooks import router as webhooks_router

api_router = APIRouter(prefix="/api")

api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(payments_router, prefix="/payments", tags=["Payments"])
api_router.include_router(cases_router, prefix="/cases", tags=["Cases"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(audit_router, prefix="/audit", tags=["Audit"])
api_router.include_router(simulate_router, prefix="/simulate", tags=["Simulate"])
api_router.include_router(policy_router, prefix="/policy", tags=["Policy"])
api_router.include_router(agent_router, prefix="/agent", tags=["Agent"])
api_router.include_router(evaluation_router, prefix="/evaluation", tags=["Evaluation"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])

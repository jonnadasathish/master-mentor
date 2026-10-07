from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    activity,
    admin,
    assessments,
    catalog,
    communication,
    content,
    data,
    export,
    gaps,
    health,
    learning,
    mocks,
    profile,
    readiness,
    reviews,
    revisions,
    skills,
    today,
)

API_PREFIX = "/api/v1"

api_router = APIRouter(prefix=API_PREFIX)
api_router.include_router(health.router)
api_router.include_router(catalog.router)
api_router.include_router(activity.router)
api_router.include_router(assessments.router)
api_router.include_router(skills.router)
api_router.include_router(admin.router)
api_router.include_router(export.router)
api_router.include_router(profile.router)
api_router.include_router(gaps.router)
api_router.include_router(revisions.router)
api_router.include_router(today.router)
api_router.include_router(readiness.router)
api_router.include_router(mocks.router)
api_router.include_router(content.router)
api_router.include_router(reviews.router)
api_router.include_router(data.router)
api_router.include_router(learning.router)
api_router.include_router(communication.router)

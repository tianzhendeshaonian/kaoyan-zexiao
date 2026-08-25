from fastapi import APIRouter

from . import schools, majors, scores, admissions, reports, recommend, users, vip


api_router = APIRouter()

api_router.include_router(users.router)
api_router.include_router(schools.router)
api_router.include_router(majors.router)
api_router.include_router(scores.router)
api_router.include_router(admissions.router)
api_router.include_router(reports.router)
api_router.include_router(recommend.router)
api_router.include_router(vip.router)


__all__ = ["api_router"]

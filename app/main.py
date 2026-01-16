from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import exam, quiz
from app.core.config import settings

app = FastAPI(
    title="ADsP Quiz Backend API",
    description="ADsP 퀴즈 생성 및 시험 관리 백엔드 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(quiz.router, prefix="/api/v1")
app.include_router(exam.router, prefix="/api/v1")


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "ADsP Quiz Backend API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}

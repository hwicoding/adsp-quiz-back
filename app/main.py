import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.api.v1 import exam, quiz, subjects
from app.core.config import settings
from app.core.logging import setup_logging
from app.models.base import get_engine

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

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
app.include_router(subjects.router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 오류 핸들러"""
    logger.warning(f"요청 검증 오류: {exc.errors()}, path={request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """데이터베이스 예외 핸들러"""
    logger.error(
        f"Database error: {exc.__class__.__name__}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    if settings.environment == "production":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error occurred"},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 핸들러 - 모든 미처리 예외를 로깅"""
    logger.error(
        f"Unhandled exception: {exc.__class__.__name__}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "query_params": dict(request.query_params),
        }
    )
    
    # 프로덕션 환경에서는 상세 에러 메시지 숨김
    if settings.environment == "production":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"},
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "type": exc.__class__.__name__,
            },
        )


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {"message": "ADsP Quiz Backend API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}


@app.get("/health/db")
async def health_check_db():
    """데이터베이스 연결 상태 확인"""
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected"},
        )

import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from app.api.v1 import exam, main_topics, quiz, subjects, sub_topics
from app.core.config import settings
from app.core.logging import setup_logging
from app.exceptions import BaseAppError
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
app.include_router(main_topics.router, prefix="/api/v1")
app.include_router(sub_topics.router, prefix="/api/v1")


def create_cors_response(
    status_code: int,
    content: dict,
    request: Request,
) -> JSONResponse:
    """CORS 헤더를 포함한 JSONResponse 생성"""
    response = JSONResponse(
        status_code=status_code,
        content=content,
    )
    # CORS 헤더 명시적 추가 (예외 핸들러에서도 CORS 헤더 보장)
    origin = request.headers.get("origin")
    if origin and origin in settings.allowed_origins_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """요청 검증 오류 핸들러"""
    logger.warning(f"요청 검증 오류: {exc.errors()}, path={request.url.path}")
    return create_cors_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
        request=request,
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
        return create_cors_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error occurred"},
            request=request,
        )
    else:
        return create_cors_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc)},
            request=request,
        )


@app.exception_handler(BaseAppError)
async def app_exception_handler(request: Request, exc: BaseAppError):
    """애플리케이션 커스텀 예외 핸들러"""
    logger.warning(
        f"Application error: {exc.__class__.__name__} - {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
        }
    )
    return create_cors_response(
        status_code=exc.status_code,
        content={"detail": exc.message},
        request=request,
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
        return create_cors_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal Server Error"},
            request=request,
        )
    else:
        return create_cors_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": str(exc),
                "type": exc.__class__.__name__,
            },
            request=request,
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

# -*- coding: utf-8 -*-
import logging
import sys
from pathlib import Path

from app.core.config import settings


def setup_logging():
    """로깅 설정"""
    log_level = logging.DEBUG if settings.environment == "development" else logging.INFO
    
    # 로그 포맷
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # 파일 핸들러 (프로덕션)
    if settings.environment == "production":
        log_dir = Path("/app/logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    if settings.environment == "production":
        root_logger.addHandler(file_handler)

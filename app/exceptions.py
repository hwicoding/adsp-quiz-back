"""커스텀 예외 클래스 정의"""


class BaseAppError(Exception):
    """애플리케이션 기본 예외 클래스"""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class GeminiServiceUnavailableError(BaseAppError):
    """Gemini API 서비스 일시적 과부하 에러 (503)"""
    
    def __init__(self, message: str = "Gemini API가 일시적으로 과부하 상태입니다. 잠시 후 다시 시도해주세요."):
        super().__init__(message, status_code=503)


class GeminiAPIKeyError(BaseAppError):
    """Gemini API 키 관련 에러 (403)"""
    
    def __init__(self, message: str = "Gemini API 키 문제로 문제 생성에 실패했습니다. 관리자에게 문의하세요."):
        super().__init__(message, status_code=403)


class QuizNotFoundError(BaseAppError):
    """문제를 찾을 수 없을 때 발생하는 예외 (404)"""
    
    def __init__(self, quiz_id: int):
        super().__init__(f"문제를 찾을 수 없습니다: {quiz_id}", status_code=404)


class SubjectNotFoundError(BaseAppError):
    """과목을 찾을 수 없을 때 발생하는 예외 (404)"""
    
    def __init__(self, subject_id: int):
        super().__init__(f"과목을 찾을 수 없습니다: {subject_id}", status_code=404)


class ExamSessionNotFoundError(BaseAppError):
    """시험 세션을 찾을 수 없을 때 발생하는 예외 (404)"""
    
    def __init__(self, exam_session_id: str):
        super().__init__(f"시험 기록을 찾을 수 없습니다: {exam_session_id}", status_code=404)


class InvalidQuizRequestError(BaseAppError):
    """잘못된 문제 요청일 때 발생하는 예외 (400)"""
    
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class MainTopicNotFoundError(BaseAppError):
    """주요항목을 찾을 수 없을 때 발생하는 예외 (404)"""
    
    def __init__(self, main_topic_id: int):
        super().__init__(f"주요항목을 찾을 수 없습니다: {main_topic_id}", status_code=404)


class SubTopicNotFoundError(BaseAppError):
    """세부항목을 찾을 수 없을 때 발생하는 예외 (404)"""
    
    def __init__(self, sub_topic_id: int):
        super().__init__(f"세부항목을 찾을 수 없습니다: {sub_topic_id}", status_code=404)

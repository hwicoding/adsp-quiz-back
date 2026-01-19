"""커스텀 예외 클래스 정의"""


class GeminiServiceUnavailableError(Exception):
    """Gemini API 서비스 일시적 과부하 에러 (503)"""
    
    def __init__(self, message: str = "Gemini API가 일시적으로 과부하 상태입니다. 잠시 후 다시 시도해주세요."):
        self.message = message
        super().__init__(self.message)

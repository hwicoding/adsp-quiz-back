import hashlib
from typing import Any

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


async def extract_transcript(video_id: str) -> str:
    """YouTube 동영상 자막 추출"""
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        transcript = transcript_list.find_transcript(["ko", "en"])
        transcript_data = transcript.fetch()
        raw_data = transcript_data.to_raw_data()
        return " ".join([item["text"] for item in raw_data])
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise ValueError(f"자막을 찾을 수 없습니다: {str(e)}")


def extract_video_id(url: str) -> str:
    """YouTube URL에서 video_id 추출"""
    if "youtube.com/watch?v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    raise ValueError("유효하지 않은 YouTube URL입니다")


def generate_hash(text: str) -> str:
    """텍스트의 MD5 해시 생성"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()

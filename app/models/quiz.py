from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Quiz(Base, TimestampMixin):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    sub_topic_id: Mapped[int | None] = mapped_column(ForeignKey("sub_topics.id"), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[int] = mapped_column(nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, default=None)
    source_hash: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    source_url: Mapped[str | None] = mapped_column(default=None)
    source_text: Mapped[str | None] = mapped_column(Text, default=None)

    subject: Mapped["Subject"] = relationship("Subject", back_populates="quizzes")
    sub_topic: Mapped["SubTopic"] = relationship("SubTopic", back_populates="quizzes")
    exam_records: Mapped[list["ExamRecord"]] = relationship(
        "ExamRecord",
        back_populates="quiz",
    )
    validations: Mapped[list["QuizValidation"]] = relationship(
        "QuizValidation",
        back_populates="quiz",
    )

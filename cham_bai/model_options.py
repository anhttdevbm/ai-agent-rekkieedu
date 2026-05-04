"""
Hằng số model / loại quiz dùng chung GUI và web — không phụ thuộc tkinter (chạy được trong Docker).
"""

from __future__ import annotations

from cham_bai.quiz_gen import QUIZ_KIND_SESSION, QUIZ_KIND_SESSION_END, QUIZ_KIND_SESSION_WARMUP

QUIZ_KIND_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Quizz đầu giờ — theo session", QUIZ_KIND_SESSION),
    ("Quizz Session đầu giờ", QUIZ_KIND_SESSION_WARMUP),
    ("Quizz Session cuối giờ", QUIZ_KIND_SESSION_END),
)

# Vision–language, free; phù hợp Chấm BTVN (đề có ảnh + đọc repo).
DEFAULT_BTVN_MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"

# Free, context lớn; phù hợp Quizz Session đầu giờ / cuối giờ (JSON 15 câu × 3 block).
DEFAULT_QUIZ_SESSION_WARMUP_END_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

MODEL_OPTIONS: tuple[str, ...] = (
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-opus-4.6",
    "deepseek/deepseek-v3.2",
    "minimax/minimax-m2.7",
    "google/gemini-3-flash-preview",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    DEFAULT_QUIZ_SESSION_WARMUP_END_MODEL,
)

IMAGE_MODEL_OPTIONS: tuple[str, ...] = (
    "black-forest-labs/flux.2-pro",
    "black-forest-labs/flux.2-flex",
    "google/gemini-2.5-flash-image-preview",
    "google/gemini-2.5-flash-image",
)

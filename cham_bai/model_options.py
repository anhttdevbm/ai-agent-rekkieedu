"""
Hằng số model / loại quiz dùng chung GUI và web — không phụ thuộc tkinter (chạy được trong Docker).
"""

from __future__ import annotations

from cham_bai.quiz_gen import QUIZ_KIND_SESSION, QUIZ_KIND_SESSION_WARMUP

QUIZ_KIND_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Quizz đầu giờ — theo session", QUIZ_KIND_SESSION),
    ("Quizz Session đầu giờ", QUIZ_KIND_SESSION_WARMUP),
)

MODEL_OPTIONS: tuple[str, ...] = (
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-opus-4.6",
    "deepseek/deepseek-v3.2",
    "minimax/minimax-m2.7",
    "google/gemini-3-flash-preview",
    "nvidia/nemotron-3-super-120b-a12b:free",
)

IMAGE_MODEL_OPTIONS: tuple[str, ...] = (
    "black-forest-labs/flux.2-pro",
    "black-forest-labs/flux.2-flex",
    "google/gemini-2.5-flash-image-preview",
    "google/gemini-2.5-flash-image",
)

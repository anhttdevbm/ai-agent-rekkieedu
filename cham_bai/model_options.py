"""
Hằng số model / loại quiz dùng chung GUI và web — không phụ thuộc tkinter (chạy được trong Docker).
"""

from __future__ import annotations

# Trùng giá trị với cham_bai.quiz_gen (không import quiz_gen — tránh vòng import khi quiz_gen dùng resolve_quiz_llm_model).
QUIZ_KIND_SESSION = "session"
QUIZ_KIND_SESSION_WARMUP = "session_warmup"
QUIZ_KIND_SESSION_END = "session_end"

QUIZ_KIND_OPTIONS: tuple[tuple[str, str], ...] = (
    ("Quizz đầu giờ — theo session", QUIZ_KIND_SESSION),
    ("Quizz Session đầu giờ", QUIZ_KIND_SESSION_WARMUP),
    ("Quizz Session cuối giờ", QUIZ_KIND_SESSION_END),
)

# Vision–language, free; phù hợp Chấm BTVN (đề có ảnh + đọc repo).
DEFAULT_BTVN_MODEL = "nvidia/nemotron-nano-12b-v2-vl:free"

# Model chat (OpenRouter /v1/chat/completions) khi sinh Excel quiz (JSON 45 câu = nhiều sub-block 5 câu + tài liệu).
# Gemma 4 26B A4B (IT): ctx ~262k, bám cấu trúc tốt, hợp pipeline session quiz.
DEFAULT_QUIZ_SESSION_WARMUP_END_CHAT_MODEL = "google/gemma-4-26b-a4b-it"

# Mặc định UI khi chọn «Quizz Session đầu giờ» / «Quizz Session cuối giờ»:
# Phải là model instruct (sinh văn bản). Các model chỉ có API embeddings không phù hợp làm mặc định — để trong MODEL_OPTIONS (nhóm embedding).
DEFAULT_QUIZ_SESSION_WARMUP_END_MODEL = DEFAULT_QUIZ_SESSION_WARMUP_END_CHAT_MODEL

# Slug OpenRouter chỉ hỗ trợ /v1/embeddings (không dùng trực tiếp cho sinh quiz).
OPENROUTER_EMBEDDING_ONLY_IDS: frozenset[str] = frozenset(
    {
        "perplexity/pplx-embed-v1-0.6b",
        "perplexity/pplx-embed-v1-4b",
        "thenlper/gte-base",
        "thenlper/gte-large",
        "intfloat/e5-base-v2",
        "intfloat/e5-large-v2",
        "intfloat/multilingual-e5-large",
        "sentence-transformers/paraphrase-minilm-l6-v2",
        "sentence-transformers/all-minilm-l12-v2",
        "sentence-transformers/all-mpnet-base-v2",
        "sentence-transformers/multi-qa-mpnet-base-dot-v1",
        "sentence-transformers/all-minilm-l6-v2",
        "baai/bge-base-en-v1.5",
        "baai/bge-large-en-v1.5",
        "baai/bge-m3",
        "qwen/qwen3-embedding-8b",
        "qwen/qwen3-embedding-4b",
        "openai/text-embedding-3-small",
    }
)


def resolve_quiz_llm_model(requested: str | None) -> tuple[str, str]:
    """
    Trả về (slug cho /v1/chat/completions, ghi chú hoặc chuỗi rỗng).
    Nếu user chọn model embedding-only, tự dùng DEFAULT_QUIZ_SESSION_WARMUP_END_CHAT_MODEL.
    """
    from cham_bai.settings import model as _or_model

    r = (requested or "").strip()
    if r in OPENROUTER_EMBEDDING_ONLY_IDS:
        chat = _or_model(DEFAULT_QUIZ_SESSION_WARMUP_END_CHAT_MODEL)
        return (
            chat,
            f"Ghi chú: «{r}» là model nhúng vector (embeddings API); sinh quiz dùng «{chat}».",
        )
    return _or_model(r if r else None), ""


MODEL_OPTIONS: tuple[str, ...] = (
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-opus-4.6",
    "deepseek/deepseek-v3.2",
    "minimax/minimax-m2.7",
    "google/gemini-3-flash-preview",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    DEFAULT_QUIZ_SESSION_WARMUP_END_MODEL,
    "openai/gpt-oss-120b",
    "qwen/qwen-turbo",
    "qwen/qwen3.5-flash-02-23",
    "qwen/qwen3-8b",
    "mistralai/mistral-nemo",
    "meta-llama/llama-3.3-70b-instruct:free",
    # Instruct (chat) — thêm lựa chọn:
    "meta-llama/llama-3.1-8b-instruct",
    "ibm-granite/granite-4.0-h-micro",
    # Embeddings OpenRouter (API /v1/embeddings — chọn thủ công: sinh quiz map sang CHAT_MODEL ở trên).
    "openai/text-embedding-3-small",
    "qwen/qwen3-embedding-4b",
    "perplexity/pplx-embed-v1-0.6b",
    "perplexity/pplx-embed-v1-4b",
    "thenlper/gte-large",
    "intfloat/e5-large-v2",
    "intfloat/multilingual-e5-large",
    "baai/bge-large-en-v1.5",
    "baai/bge-m3",
    "qwen/qwen3-embedding-8b",
)

IMAGE_MODEL_OPTIONS: tuple[str, ...] = (
    "black-forest-labs/flux.2-pro",
    "black-forest-labs/flux.2-flex",
    "google/gemini-2.5-flash-image-preview",
    "google/gemini-2.5-flash-image",
)

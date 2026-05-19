"""Highlight / format code blocks (same palette as bài đọc DOCX)."""

from __future__ import annotations

import html as html_module
import io
import keyword
import tokenize
from dataclasses import dataclass

from docx.shared import RGBColor

CODE_BLOCK_FILL = "1E1E1E"

CLR_CODE_COMMENT = RGBColor(0x9C, 0xDC, 0xFE)
CLR_CODE_KEYWORD = RGBColor(0xD1, 0x6D, 0x9A)
CLR_CODE_FUNCTION = RGBColor(0xC5, 0x86, 0xC0)
CLR_CODE_STRING = RGBColor(0xCE, 0x91, 0x78)
CLR_CODE_NUMBER = RGBColor(0xB5, 0xCE, 0xA8)
CLR_CODE_DEFAULT = RGBColor(0xD4, 0xD4, 0xD4)

_PY_RESERVED: frozenset[str] = frozenset(keyword.kwlist) | frozenset({"True", "False", "None"})


def _rgb_hex(c: RGBColor) -> str:
    return f"#{c}"


@dataclass(frozen=True)
class CodeSegment:
    text: str
    color: RGBColor


def _char_index_in_code(code: str, line_1based: int, col_0based: int) -> int:
    if line_1based < 1:
        return 0
    lines = code.splitlines(keepends=True)
    idx = 0
    for li in range(line_1based - 1):
        if li < len(lines):
            idx += len(lines[li])
    idx += col_0based
    return min(max(0, idx), len(code))


def _token_next_non_comment_newline(tokens: list, i: int):
    j = i + 1
    while j < len(tokens):
        t = tokens[j]
        if t.type in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT):
            j += 1
            continue
        return t
    return None


def _python_token_color(tok: tokenize.TokenInfo, tokens: list, i: int) -> RGBColor:
    if tok.type == tokenize.NAME:
        if tok.string in _PY_RESERVED:
            return CLR_CODE_KEYWORD
        nxt = _token_next_non_comment_newline(tokens, i)
        if nxt and nxt.type == tokenize.OP and nxt.string == "(":
            return CLR_CODE_FUNCTION
        return CLR_CODE_DEFAULT
    if tok.type == tokenize.COMMENT:
        return CLR_CODE_COMMENT
    if tok.type == tokenize.STRING:
        return CLR_CODE_STRING
    if tok.type == tokenize.NUMBER:
        return CLR_CODE_NUMBER
    return CLR_CODE_DEFAULT


def segment_python_code(code: str) -> list[CodeSegment]:
    """Tách code Python thành các đoạn kèm màu (giống khối code bài đọc)."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except tokenize.TokenError:
        return [CodeSegment(code, CLR_CODE_DEFAULT)]

    out: list[CodeSegment] = []
    cursor = 0

    def _push(piece: str, color: RGBColor) -> None:
        if not piece:
            return
        if out and out[-1].color == color:
            out[-1] = CodeSegment(out[-1].text + piece, color)
        else:
            out.append(CodeSegment(piece, color))

    for i, tok in enumerate(tokens):
        idx_s = _char_index_in_code(code, tok.start[0], tok.start[1])
        idx_e = _char_index_in_code(code, tok.end[0], tok.end[1])
        if cursor < idx_s:
            _push(code[cursor:idx_s], CLR_CODE_DEFAULT)
        if tok.type == tokenize.ENDMARKER:
            cursor = idx_e
            break
        if tok.type == tokenize.ENCODING:
            cursor = idx_e
            continue
        if idx_s >= idx_e:
            cursor = idx_e
            continue
        piece = code[idx_s:idx_e]
        _push(piece, _python_token_color(tok, tokens, i))
        cursor = idx_e
    if cursor < len(code):
        _push(code[cursor:], CLR_CODE_DEFAULT)
    return out or [CodeSegment("", CLR_CODE_DEFAULT)]


def segment_code(code: str, lang: str = "python") -> list[CodeSegment]:
    lang_n = (lang or "python").strip().lower()
    if lang_n in ("python", "py", "python3", ""):
        return segment_python_code(code)
    return [CodeSegment(code, CLR_CODE_DEFAULT)]


def style_code_run_on_dark(run, *, color: RGBColor = CLR_CODE_DEFAULT) -> None:
    from docx.shared import Pt  # noqa: PLC0415

    run.font.name = "Consolas"
    run.font.size = Pt(10)
    run.font.color.rgb = color


def apply_python_highlight_to_paragraph(p, code: str) -> None:
    """Gắn run có màu lên paragraph DOCX (nền tối gán ở caller)."""
    for seg in segment_python_code(code):
        r = p.add_run(seg.text)
        style_code_run_on_dark(r, color=seg.color)


def highlight_code_to_html(code: str, lang: str = "python") -> tuple[str, str]:
    """Trả về (html_fragment, plain_text) — html là nội dung trong <pre><code>."""
    segments = segment_code(code, lang)
    plain = "".join(s.text for s in segments)
    inner: list[str] = []
    for seg in segments:
        esc = html_module.escape(seg.text)
        if esc:
            inner.append(f'<span style="color:{_rgb_hex(seg.color)}">{esc}</span>')
    html_body = "".join(inner) if inner else ""
    return html_body, plain

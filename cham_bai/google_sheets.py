from __future__ import annotations

import json
import os
import random
import re
import unicodedata
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlparse


_SHEETS_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", re.I)


def extract_spreadsheet_id(url: str) -> str | None:
    m = _SHEETS_ID_RE.search(str(url or ""))
    return m.group(1) if m else None


def extract_gid(url: str) -> str | None:
    try:
        u = urlparse(url)
    except Exception:
        return None
    for src in (u.query or "", u.fragment or ""):
        if not src:
            continue
        qs = parse_qs(src, keep_blank_values=True)
        gid = (qs.get("gid") or [None])[0]
        if gid is not None and str(gid).strip() != "":
            return str(gid).strip()
    return None


def _norm_text(s: str) -> str:
    t = str(s or "")
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def _norm_name_for_match(s: str) -> str:
    t = _norm_text(s)
    t = re.sub(r"\(leader\)", "", t).strip()
    return t


def _col_to_a1(col_idx_1based: int) -> str:
    n = int(col_idx_1based)
    if n <= 0:
        return "A"
    out = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        out = chr(ord("A") + r) + out
    return out


def _get_service_account_creds():
    """
    Load Service Account creds from:
    - GOOGLE_APPLICATION_CREDENTIALS (path)
    - GOOGLE_SERVICE_ACCOUNT_JSON (raw json string)
    """
    # Lazy imports to avoid crashing when deps not installed.
    from google.oauth2 import service_account

    p = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
    raw = (os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or "").strip()
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    if p:
        return service_account.Credentials.from_service_account_file(p, scopes=scopes)
    if raw:
        info = json.loads(raw)
        return service_account.Credentials.from_service_account_info(info, scopes=scopes)
    raise RuntimeError(
        "Thiếu credential Google Sheets. Cần đặt GOOGLE_APPLICATION_CREDENTIALS (đường dẫn .json) "
        "hoặc GOOGLE_SERVICE_ACCOUNT_JSON (nội dung json). Sau đó share sheet quyền Editor cho email service account."
    )


def _build_sheets_service():
    from googleapiclient.discovery import build

    creds = _get_service_account_creds()
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _unwrap_values(resp: Any) -> list[list[str]]:
    if isinstance(resp, dict):
        v = resp.get("values")
        if isinstance(v, list):
            return [[str(x) if x is not None else "" for x in row] for row in v if isinstance(row, list)]
    return []


@dataclass
class SheetSessionColumns:
    sheet_name: str
    header_rows: int
    name_col: int  # 1-based
    so_bt_col: int  # 1-based
    nhan_xet_col: int  # 1-based


def detect_session_columns(
    *,
    spreadsheet_id: str,
    session_no: int,
    sheet_name: str | None = None,
    header_rows: int = 3,
) -> SheetSessionColumns:
    """
    Detect columns for a session: SESSION 08 -> (Số BT, Nhận xét).
    Strategy:
    - Read first `header_rows` rows (A1:ZZ{header_rows})
    - Find "Họ và Tên Sinh Viên" column (name_col)
    - Find "SESSION 08" group on row 1/2, then subheaders "Số BT", "Nhận xét" on last header row.
    """
    svc = _build_sheets_service()
    sh = sheet_name or "Sheet1"
    rng = f"'{sh}'!A1:ZZ{header_rows}"
    resp = svc.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
    grid = _unwrap_values(resp)
    if not grid:
        raise RuntimeError("Không đọc được header sheet.")

    # Normalize to rectangular
    width = max((len(r) for r in grid), default=0)
    grid = [r + [""] * (width - len(r)) for r in grid]

    # Find name column by scanning header rows
    name_col = 0
    target_name = _norm_text("Họ và Tên Sinh Viên")
    for c in range(width):
        for r in range(len(grid)):
            if _norm_text(grid[r][c]) == target_name:
                name_col = c + 1
                break
        if name_col:
            break
    if not name_col:
        # fallback: any header contains "Họ và Tên"
        for c in range(width):
            for r in range(len(grid)):
                if "ho va ten" in _norm_text(grid[r][c]):
                    name_col = c + 1
                    break
            if name_col:
                break
    if not name_col:
        raise RuntimeError("Không tìm thấy cột 'Họ và Tên Sinh Viên' trong header.")

    sess_label = f"SESSION {int(session_no):02d}"
    sess_norm = _norm_text(sess_label)
    # Find session group columns: any cell exactly equals "SESSION 08"
    sess_cols: list[int] = []
    for r in range(len(grid)):
        for c in range(width):
            if _norm_text(grid[r][c]) == sess_norm:
                sess_cols.append(c + 1)
    if not sess_cols:
        # fallback: contains "SESSION 08"
        for r in range(len(grid)):
            for c in range(width):
                if sess_norm in _norm_text(grid[r][c]):
                    sess_cols.append(c + 1)
    if not sess_cols:
        raise RuntimeError(f"Không tìm thấy group '{sess_label}' trong header.")

    # The session group is usually merged; we need to locate subheaders below it.
    # We approximate by scanning from the first session col to the right until next "SESSION".
    start = min(sess_cols)
    end = width
    for c in range(start + 1, width + 1):
        cell = grid[0][c - 1] if grid else ""
        if _norm_text(cell).startswith("session ") and c != start:
            end = c - 1
            break

    sub = grid[-1]  # last header row
    so_bt_col = 0
    nhan_xet_col = 0
    for c in range(start, end + 1):
        v = _norm_text(sub[c - 1])
        if v == _norm_text("Số BT"):
            so_bt_col = c
        if v == _norm_text("Nhận xét"):
            nhan_xet_col = c

    if not so_bt_col or not nhan_xet_col:
        raise RuntimeError(f"Không tìm thấy cột con 'Số BT'/'Nhận xét' cho {sess_label}.")

    return SheetSessionColumns(
        sheet_name=sh,
        header_rows=header_rows,
        name_col=name_col,
        so_bt_col=so_bt_col,
        nhan_xet_col=nhan_xet_col,
    )


def update_session_cells(
    *,
    spreadsheet_id: str,
    cols: SheetSessionColumns,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    rows: [{fullName, so_bt_text, nhan_xet}]
    - Find student row by matching fullName in name column (from row header_rows+1 down)
    - Batch update so_bt_col and nhan_xet_col
    """
    svc = _build_sheets_service()
    sh = cols.sheet_name

    # Read name column values to map to row numbers.
    name_a1 = _col_to_a1(cols.name_col)
    start_row = cols.header_rows + 1
    rng = f"'{sh}'!{name_a1}{start_row}:{name_a1}"
    resp = svc.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=rng).execute()
    vals = _unwrap_values(resp)
    # vals is [[name], [name], ...]
    name_to_row: dict[str, int] = {}
    for i, row in enumerate(vals):
        nm = row[0] if row else ""
        key = _norm_name_for_match(nm)
        if key and key not in name_to_row:
            name_to_row[key] = start_row + i

    updates = []
    miss = []

    so_a1 = _col_to_a1(cols.so_bt_col)
    nx_a1 = _col_to_a1(cols.nhan_xet_col)

    for r in rows:
        full = str(r.get("fullName") or "").strip()
        if not full:
            continue
        key = _norm_name_for_match(full)
        row_no = name_to_row.get(key)
        if not row_no:
            miss.append(full)
            continue

        so_bt = str(r.get("so_bt_text") or "").strip()
        nx = str(r.get("nhan_xet") or "").strip()
        if len(nx) > 1000:
            nx = nx[:1000].rstrip() + "…"

        updates.append(
            {
                "range": f"'{sh}'!{so_a1}{row_no}",
                "values": [[so_bt]],
            }
        )
        updates.append(
            {
                "range": f"'{sh}'!{nx_a1}{row_no}",
                "values": [[nx]],
            }
        )

    if not updates:
        return {"ok": True, "updated": 0, "missing": miss}

    body = {"valueInputOption": "USER_ENTERED", "data": updates}
    svc.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()
    return {"ok": True, "updated": len(updates) // 2, "missing": miss}


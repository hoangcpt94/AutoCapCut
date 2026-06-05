"""Đăng ký draft với CapCut để bản mới (7.x/8.x) nhận diện được.

VẤN ĐỀ:
    CapCut bản mới KHÔNG quét thư mục để tìm draft. Nó đọc danh sách dự án từ
    file index `root_meta_info.json` (trường `all_draft_store`). pycapcut tạo
    folder + draft_content.json nhưng:
      - để `draft_meta_info.json` ở dạng template rỗng (draft_name="", path="",
        draft_id bị hardcode cứng cho mọi draft);
      - KHÔNG thêm entry vào `all_draft_store`.
    => Khi mở, CapCut coi folder là rác và TỰ XÓA nó.

GIẢI PHÁP (module này):
    1. Sinh draft_id mới (UUID) cho mỗi draft.
    2. Điền đầy đủ metadata thật vào draft_meta_info.json:
       draft_name, draft_fold_path, draft_root_path, draft_id, tm_duration, mốc thời gian.
    3. Thêm/cập nhật entry tương ứng trong all_draft_store của root_meta_info.json.

An toàn:
    - Luôn backup root_meta_info.json (đuôi .backup.json) trước khi sửa.
    - Nếu trùng draft cùng tên/đường dẫn thì cập nhật entry cũ, không nhân bản.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

DRAFT_META_FILE = "draft_meta_info.json"
ROOT_META_FILE = "root_meta_info.json"


def _now_us() -> int:
    """Thời điểm hiện tại theo micro giây (CapCut dùng đơn vị này cho mốc thời gian)."""
    return int(time.time() * 1_000_000)


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def _to_capcut_path(p: str) -> str:
    """CapCut lưu đường dẫn với dấu '/'."""
    return os.path.normpath(p).replace("\\", "/")


def _read_duration_us(draft_dir: str) -> int:
    """Đọc tổng thời lượng (us) từ draft_content.json."""
    content = _read_json(os.path.join(draft_dir, "draft_content.json"))
    if content and isinstance(content.get("duration"), (int, float)):
        return int(content["duration"])
    return 0


def register_draft(draft_root: str, draft_name: str) -> str:
    """Đăng ký draft vào CapCut. Trả về draft_id đã dùng.

    Args:
        draft_root: thư mục draft gốc của CapCut (chứa root_meta_info.json).
        draft_name: tên draft (= tên thư mục con).
    """
    draft_dir = os.path.join(draft_root, draft_name)
    if not os.path.isdir(draft_dir):
        raise FileNotFoundError(f"Không thấy thư mục draft: {draft_dir}")

    draft_id = str(uuid.uuid4()).upper()
    now = _now_us()
    duration = _read_duration_us(draft_dir)

    _update_draft_meta(draft_dir, draft_root, draft_name, draft_id, now, duration)
    _update_root_index(draft_root, draft_dir, draft_name, draft_id, now, duration)
    return draft_id


def _update_draft_meta(draft_dir: str, draft_root: str, draft_name: str,
                       draft_id: str, now: int, duration: int) -> None:
    """Điền metadata thật vào draft_meta_info.json của draft."""
    meta_path = os.path.join(draft_dir, DRAFT_META_FILE)
    meta = _read_json(meta_path) or {}

    meta.update({
        "draft_id": draft_id,
        "draft_name": draft_name,
        "draft_fold_path": _to_capcut_path(draft_dir),
        "draft_root_path": _to_capcut_path(draft_root),
        "draft_cover": "draft_cover.jpg",
        "tm_duration": duration,
        "tm_draft_create": now,
        "tm_draft_modified": now,
        "tm_draft_removed": 0,
    })
    _write_json(meta_path, meta)


def _make_store_entry(draft_dir: str, draft_name: str, draft_id: str,
                      now: int, duration: int) -> Dict[str, Any]:
    """Tạo một entry cho all_draft_store."""
    return {
        "draft_id": draft_id,
        "draft_name": draft_name,
        "draft_fold_path": _to_capcut_path(draft_dir),
        "draft_root_path": _to_capcut_path(os.path.dirname(draft_dir)),
        "draft_cover": _to_capcut_path(os.path.join(draft_dir, "draft_cover.jpg")),
        "draft_json_file": _to_capcut_path(os.path.join(draft_dir, "draft_content.json")),
        "draft_timeline_materials_size": 0,
        "tm_draft_create": now,
        "tm_draft_modified": now,
        "tm_duration": duration,
        "type": 0,
    }


def _update_root_index(draft_root: str, draft_dir: str, draft_name: str,
                       draft_id: str, now: int, duration: int) -> None:
    """Thêm/cập nhật entry của draft trong root_meta_info.json (all_draft_store)."""
    root_path = os.path.join(draft_root, ROOT_META_FILE)
    root_meta = _read_json(root_path)

    if root_meta is None:
        root_meta = {
            "all_draft_store": [],
            "draft_ids": 0,
            "root_path": _to_capcut_path(draft_root),
        }
    else:
        # Backup 1 lần trước khi sửa (giữ bản gốc đầu tiên).
        backup = os.path.join(draft_root, "root_meta_info.backup.json")
        if not os.path.isfile(backup):
            try:
                _write_json(backup, root_meta)
            except OSError:
                pass

    store: List[Dict[str, Any]] = root_meta.get("all_draft_store") or []
    target_fold = _to_capcut_path(draft_dir)

    # Bỏ entry cũ trùng tên hoặc trùng đường dẫn (tránh nhân bản khi chạy lại).
    store = [
        e for e in store
        if e.get("draft_fold_path") != target_fold and e.get("draft_name") != draft_name
    ]
    store.insert(0, _make_store_entry(draft_dir, draft_name, draft_id, now, duration))

    root_meta["all_draft_store"] = store
    if isinstance(root_meta.get("draft_ids"), int):
        root_meta["draft_ids"] = root_meta["draft_ids"] + 1
    _write_json(root_path, root_meta)

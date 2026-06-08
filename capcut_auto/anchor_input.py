"""Đọc INPUT của một tập theo chế độ neo (anchor).

Mỗi tập là một thư mục, ví dụ:

    tap_01/
    ├── mapping.jsonl     # hoặc mapping.json / input.txt — danh sách cặp ảnh<->câu
    ├── voiceover.wav     # (hoặc .mp3/.m4a...) file voiceover
    └── images/           # thư mục ảnh (hoặc ảnh để thẳng trong tập)
        ├── 1.png
        ├── 2.png
        └── ...

File mapping chấp nhận 3 dạng:
    1. JSON Lines: mỗi dòng một object
       {"image_file": "1.png", "anchor_phrase": "What if you fell into a black hole?"}
    2. JSON array:
       [{"image_file": "1.png", "anchor_phrase": "..."}, ...]
    3. Nhiều object dính liền nhau trên cùng dòng/khối (không xuống dòng):
       {"image_file":"1.png",...}{"image_file":"2.png",...}

Trường:
    - image_file   (bắt buộc): tên file ảnh. Khớp theo thứ tự ưu tiên:
        1) khớp tên chính xác trong images/ rồi tới gốc tập;
        2) khớp theo SỐ Ở ĐẦU TÊN FILE. Nhờ vậy mapping ghi "01.png" vẫn khớp
           với ảnh thật tên dài như "01_black_hole_intro.png".
    - anchor_phrase(bắt buộc): cụm từ thật trong lời thoại để neo thời gian.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import IMAGE_EXTENSIONS, AUDIO_EXTENSIONS

# Lấy CỤM SỐ ĐẦU TIÊN trong tên file (phần prefix), vd:
#   "01_black_hole.png" -> 1 ; "7.png" -> 7 ; "ep02-scene10.jpg" -> 2
_LEADING_NUM_RE = re.compile(r"^\D*(\d+)")

# Tên file mapping được dò tự động (theo thứ tự ưu tiên).
_MAPPING_NAMES = ("mapping.jsonl", "mapping.json", "input.jsonl", "input.json", "input.txt", "anchors.jsonl")
# Tên thư mục ảnh con được dò tự động.
_IMAGE_SUBDIRS = ("images", "image", "img", "imgs")


@dataclass
class AnchorItem:
    """Một cặp ảnh <-> cụm từ neo."""

    image_path: str
    anchor_phrase: str


@dataclass
class EpisodeInput:
    """Toàn bộ input đã phân giải của một tập."""

    items: List[AnchorItem]
    voiceover_path: str
    mapping_path: str
    images_dir: str
    warnings: List[str] = field(default_factory=list)


def _decode_concatenated_json(text: str) -> List[dict]:
    """Giải mã chuỗi gồm nhiều object JSON nối nhau (có/không xuống dòng).

    Hỗ trợ cả JSON array, JSON Lines, lẫn dạng dính liền {..}{..}.
    """
    text = text.strip()
    if not text:
        return []

    # Thử nguyên khối: array hoặc 1 object.
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            return [o for o in obj if isinstance(o, dict)]
        if isinstance(obj, dict):
            return [obj]
    except json.JSONDecodeError:
        pass

    # Quét tuần tự bằng raw_decode để bóc từng object một.
    decoder = json.JSONDecoder()
    items: List[dict] = []
    idx = 0
    n = len(text)
    while idx < n:
        while idx < n and text[idx] in " \t\r\n,":
            idx += 1
        if idx >= n:
            break
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Không phân tích được file mapping tại ký tự {idx}: {exc.msg}"
            ) from exc
        if isinstance(obj, dict):
            items.append(obj)
        elif isinstance(obj, list):
            items.extend(o for o in obj if isinstance(o, dict))
        idx = end
    return items


def parse_mapping(path: str) -> List[dict]:
    """Đọc file mapping và trả về danh sách dict thô."""
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()
    objs = _decode_concatenated_json(text)
    if not objs:
        raise ValueError(f"File mapping rỗng hoặc không hợp lệ: {path}")
    return objs


def _find_mapping_file(episode_dir: str) -> str:
    for name in _MAPPING_NAMES:
        cand = os.path.join(episode_dir, name)
        if os.path.isfile(cand):
            return cand
    raise FileNotFoundError(
        f"Không tìm thấy file mapping trong {episode_dir} "
        f"(dò: {', '.join(_MAPPING_NAMES)})."
    )


def _find_images_dir(episode_dir: str) -> str:
    for sub in _IMAGE_SUBDIRS:
        cand = os.path.join(episode_dir, sub)
        if os.path.isdir(cand):
            return cand
    # Không có thư mục con: dùng ảnh nằm thẳng trong tập.
    return episode_dir


def _find_voiceover(episode_dir: str) -> str:
    """Tìm file voiceover trong tập (file audio đầu tiên theo tên)."""
    # Ưu tiên tên phổ biến.
    for base in ("voiceover", "voice", "vo", "audio"):
        for ext in AUDIO_EXTENSIONS:
            cand = os.path.join(episode_dir, base + ext)
            if os.path.isfile(cand):
                return cand
    # Nếu không, lấy file audio bất kỳ trong tập.
    candidates = sorted(
        os.path.join(episode_dir, n)
        for n in os.listdir(episode_dir)
        if os.path.splitext(n)[1].lower() in AUDIO_EXTENSIONS
    )
    if candidates:
        return candidates[0]
    raise FileNotFoundError(
        f"Không tìm thấy file voiceover (audio) trong {episode_dir}."
    )


def _leading_number(name: str) -> Optional[int]:
    """Trả về số nguyên ở đầu tên file (bỏ phần mở rộng), hoặc None nếu không có.

    Ví dụ: '01_black_hole.png' -> 1, '7.png' -> 7, 'scene_3.jpg' -> 3,
    'intro.png' -> None.
    """
    stem = os.path.splitext(os.path.basename(name))[0]
    m = _LEADING_NUM_RE.match(stem)
    return int(m.group(1)) if m else None


def _index_images_by_number(images_dir: str) -> Dict[int, str]:
    """Quét thư mục ảnh, lập bản đồ {số prefix -> đường dẫn ảnh}.

    Nếu nhiều ảnh cùng số prefix thì giữ ảnh có tên nhỏ nhất (ổn định, có cảnh báo
    ở nơi gọi nếu cần). Chỉ tính các file là ảnh hợp lệ.
    """
    mapping: Dict[int, str] = {}
    if not os.path.isdir(images_dir):
        return mapping
    for name in sorted(os.listdir(images_dir)):
        if os.path.splitext(name)[1].lower() not in IMAGE_EXTENSIONS:
            continue
        num = _leading_number(name)
        if num is None:
            continue
        # Giữ ảnh đầu tiên (sau sort) cho mỗi số -> ổn định.
        mapping.setdefault(num, os.path.join(images_dir, name))
    return mapping


def _resolve_image(
    image_file: str,
    images_dir: str,
    episode_dir: str,
    number_index: Dict[int, str],
) -> str:
    """Tìm đường dẫn thực của ảnh.

    Thứ tự ưu tiên:
        1. Đường dẫn tuyệt đối đã tồn tại.
        2. Khớp tên file chính xác trong images_dir, rồi gốc tập.
        3. Khớp theo SỐ PREFIX: tên thật của ảnh có thể dài hơn mapping
           (vd mapping ghi '01.png' nhưng file thật là '01_black_hole_intro.png').
           Lấy số ở đầu image_file rồi tra trong number_index.
    """
    # 1. Tuyệt đối.
    if os.path.isabs(image_file) and os.path.isfile(image_file):
        return image_file

    # 2. Khớp tên chính xác.
    for base in (images_dir, episode_dir):
        cand = os.path.join(base, image_file)
        if os.path.isfile(cand):
            return cand

    # 3. Khớp theo số prefix.
    num = _leading_number(image_file)
    if num is not None and num in number_index:
        return number_index[num]

    hint = f" (số prefix={num})" if num is not None else ""
    raise FileNotFoundError(
        f"Không tìm thấy ảnh '{image_file}'{hint}. Đã thử khớp tên chính xác trong "
        f"{images_dir} và {episode_dir}, và khớp theo số thứ tự đầu tên file."
    )


def load_episode(
    episode_dir: str,
    *,
    mapping_path: Optional[str] = None,
    images_dir: Optional[str] = None,
    voiceover_path: Optional[str] = None,
    skip_missing_images: bool = False,
) -> EpisodeInput:
    """Phân giải toàn bộ input của một tập.

    Các tham số tùy chọn cho phép ghi đè thủ công nếu cấu trúc thư mục khác.

    skip_missing_images:
        False (mặc định) -> mục nào không tìm được ảnh sẽ raise lỗi (an toàn).
        True             -> bỏ qua mục thiếu ảnh, ghi cảnh báo, vẫn chạy tiếp.
    """
    if not os.path.isdir(episode_dir):
        raise FileNotFoundError(f"Không thấy thư mục tập: {episode_dir}")

    mapping_path = mapping_path or _find_mapping_file(episode_dir)
    images_dir = images_dir or _find_images_dir(episode_dir)
    voiceover_path = voiceover_path or _find_voiceover(episode_dir)

    raw = parse_mapping(mapping_path)

    # Lập sẵn bản đồ số-prefix -> ảnh thật (để khớp khi tên file dài hơn mapping).
    number_index = _index_images_by_number(images_dir)

    warnings: List[str] = []
    items: List[AnchorItem] = []
    used_paths: Dict[str, int] = {}
    skipped = 0
    for i, obj in enumerate(raw):
        image_file = obj.get("image_file") or obj.get("image") or obj.get("img")
        phrase = obj.get("anchor_phrase") or obj.get("anchor") or obj.get("phrase")
        if not image_file or not phrase:
            raise ValueError(
                f"Mục thứ {i + 1} trong mapping thiếu 'image_file' hoặc 'anchor_phrase': {obj}"
            )
        try:
            image_path = _resolve_image(str(image_file), images_dir, episode_dir, number_index)
        except FileNotFoundError as exc:
            if not skip_missing_images:
                raise
            skipped += 1
            warnings.append(
                f"Mục #{i + 1} (image_file='{image_file}') không có ảnh -> bỏ qua anchor: "
                f"\"{str(phrase).strip()[:50]}\""
            )
            continue
        used_paths[image_path] = used_paths.get(image_path, 0) + 1
        items.append(AnchorItem(image_path=image_path, anchor_phrase=str(phrase).strip()))

    if not items:
        raise ValueError(
            f"Mapping không có mục nào dùng được (thiếu ảnh toàn bộ?): {mapping_path}"
        )

    if skipped:
        warnings.append(
            f"Đã bỏ qua {skipped}/{len(raw)} mục do thiếu ảnh. "
            f"Dùng {len(items)} ảnh có thật."
        )

    # Cảnh báo nếu một ảnh thật bị nhiều mục cùng trỏ tới (thường do trùng số prefix).
    dups = [p for p, c in used_paths.items() if c > 1]
    if dups:
        names = ", ".join(os.path.basename(p) for p in dups)
        warnings.append(f"Một số ảnh được dùng cho nhiều anchor (trùng số prefix?): {names}")

    return EpisodeInput(
        items=items,
        voiceover_path=voiceover_path,
        mapping_path=mapping_path,
        images_dir=images_dir,
        warnings=warnings,
    )

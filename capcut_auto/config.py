"""Cấu hình dự án và tiện ích phát hiện thư mục draft của CapCut."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional, Tuple

# Phần mở rộng ảnh được hỗ trợ
IMAGE_EXTENSIONS: Tuple[str, ...] = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif")
# Phần mở rộng audio được hỗ trợ
AUDIO_EXTENSIONS: Tuple[str, ...] = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")


@dataclass
class ProjectConfig:
    """Toàn bộ tham số đầu vào cho một lần chạy (chế độ neo)."""

    input_dir: Optional[str] = None
    """Thư mục input của một tập: chứa mapping ảnh<->anchor_phrase, voiceover, ảnh."""
    anchor_min_score: float = 0.45
    """Ngưỡng fuzzy-match coi như tìm thấy anchor trong lời thoại (0..1)."""

    skip_missing_images: bool = False
    """True: bỏ qua mục mapping không tìm được ảnh (kèm cảnh báo) thay vì báo lỗi."""

    images_dir: str = ""
    """Thư mục ảnh. Thường để trống và được phân giải từ input_dir."""
    voiceover_path: str = ""
    """File voiceover. Thường để trống và được phân giải từ input_dir."""

    draft_name: str = "auto_capcut_project"
    """Tên draft sẽ tạo trong thư mục CapCut."""
    draft_root: Optional[str] = None
    """Thư mục draft gốc của CapCut. None = tự phát hiện."""
    output_dir: Optional[str] = None
    """Nếu set, ghi draft ra đây thay vì thư mục CapCut (dùng để xem trước)."""

    width: int = 1080
    height: int = 1920
    fps: int = 30
    """Khung hình mặc định: dọc 1080x1920 (phù hợp short/reels). Đổi nếu cần."""

    whisper_model: str = "base"
    """Kích thước model Whisper: tiny/base/small/medium/large-v3."""
    language: Optional[str] = None
    """Mã ngôn ngữ voiceover (vd 'en', 'vi'). None = tự nhận diện."""

    add_subtitles: bool = True
    """Có thêm track phụ đề vào draft không."""

    transition: Optional[str] = None
    """Tên transition giữa các ảnh, vd 'dissolve'. None = không thêm."""

    cache_dir: str = field(default=".capcut_auto_cache")
    """Thư mục cache transcript."""

    model_cache_dir: Optional[str] = None
    """Thư mục lưu model Whisper tải về. None = mặc định của HuggingFace (ổ C).
    Đặt sang ổ còn nhiều dung lượng nếu ổ hệ thống gần đầy."""

    def validate(self) -> None:
        if not self.input_dir:
            raise ValueError("Thiếu input_dir. Hãy truyền --input-dir trỏ tới thư mục tập.")
        if not os.path.isdir(self.input_dir):
            raise FileNotFoundError(f"Không tìm thấy thư mục input: {self.input_dir}")


# Vị trí mặc định thư mục draft CapCut trên các HĐH khác nhau
_WIN_CANDIDATES = [
    r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft",
    r"%APPDATA%\CapCut\User Data\Projects\com.lveditor.draft",
    r"%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft",
]
_MAC_CANDIDATES = [
    "~/Movies/CapCut/User Data/Projects/com.lveditor.draft",
    "~/Library/Application Support/CapCut/User Data/Projects/com.lveditor.draft",
]


def find_capcut_draft_folder() -> Optional[str]:
    """Cố gắng tự phát hiện thư mục draft của CapCut. Trả về None nếu không thấy."""
    candidates = _WIN_CANDIDATES if os.name == "nt" else _MAC_CANDIDATES
    for raw in candidates:
        path = os.path.expandvars(os.path.expanduser(raw))
        if os.path.isdir(path):
            return path
    return None

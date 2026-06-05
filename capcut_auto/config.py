"""Cấu hình dự án và tiện ích phát hiện thư mục draft của CapCut."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Phần mở rộng ảnh được hỗ trợ
IMAGE_EXTENSIONS: Tuple[str, ...] = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif")
# Phần mở rộng audio được hỗ trợ
AUDIO_EXTENSIONS: Tuple[str, ...] = (".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg")


@dataclass
class ProjectConfig:
    """Toàn bộ tham số đầu vào cho một lần chạy."""

    images_dir: str
    """Thư mục chứa ảnh."""
    voiceover_path: str
    """Đường dẫn file voiceover (audio)."""
    script_path: Optional[str] = None
    """File script (txt). Nếu None thì lấy text trực tiếp từ Whisper."""

    draft_name: str = "auto_capcut_project"
    """Tên draft sẽ tạo trong thư mục CapCut."""
    draft_root: Optional[str] = None
    """Thư mục draft gốc của CapCut. None = tự phát hiện."""
    output_dir: Optional[str] = None
    """Nếu set, ghi draft ra đây thay vì thư mục CapCut (dùng để test)."""

    width: int = 1080
    height: int = 1920
    fps: int = 30
    """Khung hình mặc định: dọc 1080x1920 (phù hợp short/reels). Đổi nếu cần."""

    whisper_model: str = "base"
    """Kích thước model Whisper: tiny/base/small/medium/large-v3."""
    language: Optional[str] = None
    """Mã ngôn ngữ voiceover (vd 'en', 'vi'). None = tự nhận diện."""

    clip_model: str = "clip-ViT-B-32-multilingual-v1"
    """Model sentence-transformers đa ngôn ngữ để ghép ảnh-text."""

    add_subtitles: bool = True
    """Có thêm track phụ đề vào draft không."""
    one_image_per_segment: bool = True
    """True: mỗi đoạn 1 ảnh. False: cho phép lặp/chia ảnh."""
    allow_image_reuse: bool = False
    """Cho phép dùng lại 1 ảnh cho nhiều đoạn khi thiếu ảnh."""

    transition: Optional[str] = None
    """Tên transition giữa các ảnh, vd 'dissolve'. None = không thêm."""

    cache_dir: str = field(default=".capcut_auto_cache")
    """Thư mục cache embeddings/transcript."""

    model_cache_dir: Optional[str] = None
    """Thư mục lưu model Whisper/CLIP tải về. None = mặc định của HuggingFace (ổ C).
    Đặt sang ổ còn nhiều dung lượng nếu ổ hệ thống gần đầy."""

    def validate(self) -> None:
        if not os.path.isdir(self.images_dir):
            raise FileNotFoundError(f"Không tìm thấy thư mục ảnh: {self.images_dir}")
        if not os.path.isfile(self.voiceover_path):
            raise FileNotFoundError(f"Không tìm thấy file voiceover: {self.voiceover_path}")
        if self.script_path is not None and not os.path.isfile(self.script_path):
            raise FileNotFoundError(f"Không tìm thấy file script: {self.script_path}")

    def list_images(self) -> List[str]:
        """Trả về danh sách đường dẫn ảnh, sắp xếp theo tên."""
        files = []
        for name in os.listdir(self.images_dir):
            if os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS:
                files.append(os.path.join(self.images_dir, name))
        files.sort()
        return files


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

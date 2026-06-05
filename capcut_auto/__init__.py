"""capcut_auto - Tự động ghép ảnh khớp voiceover thành draft CapCut.

Pipeline:
    1. transcriber  : tách timing từng đoạn từ file voiceover (faster-whisper)
    2. script_utils : đọc / căn chỉnh script làm phụ đề
    3. image_matcher: phân tích ảnh (CLIP đa ngôn ngữ) và ghép ảnh khớp ngữ nghĩa
    4. draft_builder: sinh draft_content.json cho CapCut (pycapcut)
    5. pipeline     : điều phối toàn bộ các bước trên
"""

__version__ = "0.1.0"

from .config import ProjectConfig, find_capcut_draft_folder
from .transcriber import Segment

__all__ = ["ProjectConfig", "find_capcut_draft_folder", "Segment", "__version__"]

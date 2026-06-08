"""capcut_auto - Ghép ảnh theo anchor_phrase khớp voiceover thành draft CapCut.

Pipeline (chế độ neo):
    1. anchor_input : đọc mapping ảnh<->anchor_phrase + dò voiceover/ảnh của một tập
    2. transcriber  : lấy word-timestamps từ voiceover (faster-whisper)
    3. aligner      : forced-align từng anchor_phrase vào timeline
    4. draft_builder: sinh draft_content.json cho CapCut (pycapcut)
    5. pipeline     : điều phối toàn bộ các bước trên
"""

__version__ = "0.2.0"

from .config import ProjectConfig, find_capcut_draft_folder
from .transcriber import Segment, Word

__all__ = ["ProjectConfig", "find_capcut_draft_folder", "Segment", "Word", "__version__"]

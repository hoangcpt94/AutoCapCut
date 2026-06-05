"""Tạo sẵn một bộ INPUT mẫu hoàn chỉnh để chạy thử capcut_auto.

Sinh ra trong thư mục ./sample_input:
    sample_input/
    ├── images/           6 ảnh chủ đề rõ ràng (vẽ bằng PIL)
    │   ├── 01_sunrise_mountain.png
    │   ├── 02_ocean_beach.png
    │   ├── 03_green_forest.png
    │   ├── 04_city_night.png
    │   ├── 05_desert_dunes.png
    │   └── 06_snow_winter.png
    ├── voiceover.wav     giọng đọc tiếng Anh (Windows SAPI) đọc 6 câu
    └── script.txt        nội dung lời đọc (mỗi câu 1 dòng)

Cách dùng:
    .venv\\Scripts\\python.exe make_input.py

Sau đó tạo video từ bộ input này:
    .venv\\Scripts\\python.exe -m capcut_auto ^
        --images "sample_input\\images" ^
        --voiceover "sample_input\\voiceover.wav" ^
        --script "sample_input\\script.txt" ^
        --model-cache-dir "D:\\capcut_auto_models" ^
        --output-dir "sample_input\\out_draft"
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(HERE, "sample_input")
IMAGES_DIR = os.path.join(INPUT_DIR, "images")


def _draw(path, bg_top, bg_bottom, label, shapes):
    """Vẽ một ảnh 1280x720 với nền gradient dọc + các hình khối + nhãn chữ."""
    from PIL import Image, ImageDraw

    w, h = 1280, 720
    img = Image.new("RGB", (w, h), bg_top)
    draw = ImageDraw.Draw(img)

    # Gradient dọc đơn giản từ bg_top -> bg_bottom
    for y in range(h):
        t = y / (h - 1)
        r = int(bg_top[0] * (1 - t) + bg_bottom[0] * t)
        g = int(bg_top[1] * (1 - t) + bg_bottom[1] * t)
        b = int(bg_top[2] * (1 - t) + bg_bottom[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    for s in shapes:
        if s["type"] == "rect":
            draw.rectangle(s["box"], fill=s["color"])
        elif s["type"] == "ellipse":
            draw.ellipse(s["box"], fill=s["color"])
        elif s["type"] == "polygon":
            draw.polygon(s["points"], fill=s["color"])

    # Nhãn (chữ trắng góc trên) — giúp CLIP và người xem nhận diện chủ đề
    draw.text((40, 40), label, fill=(255, 255, 255))
    img.save(path)


def make_images():
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # 01 - Bình minh trên núi
    _draw(
        os.path.join(IMAGES_DIR, "01_sunrise_mountain.png"),
        (255, 170, 80), (255, 230, 150), "sunrise over the mountains",
        [
            {"type": "ellipse", "box": [540, 140, 740, 340], "color": (255, 245, 200)},
            {"type": "polygon", "points": [(0, 720), (350, 360), (700, 720)], "color": (90, 70, 110)},
            {"type": "polygon", "points": [(450, 720), (820, 320), (1280, 720)], "color": (70, 55, 95)},
        ],
    )

    # 02 - Biển và bãi cát
    _draw(
        os.path.join(IMAGES_DIR, "02_ocean_beach.png"),
        (60, 170, 230), (20, 110, 190), "blue ocean and sandy beach",
        [
            {"type": "ellipse", "box": [950, 80, 1130, 260], "color": (255, 240, 180)},
            {"type": "rect", "box": [0, 470, 1280, 560], "color": (40, 90, 160)},
            {"type": "rect", "box": [0, 560, 1280, 720], "color": (240, 220, 140)},
        ],
    )

    # 03 - Rừng xanh
    _draw(
        os.path.join(IMAGES_DIR, "03_green_forest.png"),
        (120, 200, 120), (20, 90, 40), "lush green forest with tall trees",
        [
            {"type": "rect", "box": [300, 380, 360, 640], "color": (90, 60, 30)},
            {"type": "ellipse", "box": [220, 180, 440, 430], "color": (20, 110, 40)},
            {"type": "rect", "box": [640, 360, 700, 640], "color": (90, 60, 30)},
            {"type": "ellipse", "box": [560, 150, 780, 410], "color": (15, 95, 35)},
            {"type": "rect", "box": [960, 400, 1015, 640], "color": (90, 60, 30)},
            {"type": "ellipse", "box": [880, 220, 1095, 450], "color": (25, 120, 45)},
        ],
    )

    # 04 - Thành phố về đêm
    _draw(
        os.path.join(IMAGES_DIR, "04_city_night.png"),
        (20, 20, 60), (5, 5, 25), "city skyline at night with bright lights",
        [
            {"type": "rect", "box": [150, 260, 290, 720], "color": (40, 40, 90)},
            {"type": "rect", "box": [330, 160, 470, 720], "color": (55, 55, 110)},
            {"type": "rect", "box": [520, 320, 660, 720], "color": (45, 45, 95)},
            {"type": "rect", "box": [720, 200, 860, 720], "color": (60, 60, 120)},
            {"type": "rect", "box": [910, 300, 1050, 720], "color": (50, 50, 100)},
            # cửa sổ sáng
            {"type": "rect", "box": [360, 200, 390, 230], "color": (255, 230, 120)},
            {"type": "rect", "box": [410, 260, 440, 290], "color": (255, 230, 120)},
            {"type": "rect", "box": [760, 240, 790, 270], "color": (255, 230, 120)},
            {"type": "rect", "box": [950, 340, 980, 370], "color": (255, 230, 120)},
        ],
    )

    # 05 - Sa mạc cồn cát
    _draw(
        os.path.join(IMAGES_DIR, "05_desert_dunes.png"),
        (250, 200, 120), (210, 150, 70), "golden desert sand dunes",
        [
            {"type": "ellipse", "box": [120, 100, 280, 260], "color": (255, 240, 190)},
            {"type": "polygon", "points": [(0, 720), (500, 460), (1280, 720)], "color": (225, 170, 90)},
            {"type": "polygon", "points": [(300, 720), (900, 520), (1280, 720)], "color": (200, 140, 70)},
        ],
    )

    # 06 - Mùa đông tuyết trắng
    _draw(
        os.path.join(IMAGES_DIR, "06_snow_winter.png"),
        (200, 225, 245), (150, 185, 220), "snowy winter landscape",
        [
            {"type": "rect", "box": [0, 540, 1280, 720], "color": (240, 248, 255)},
            {"type": "polygon", "points": [(200, 540), (430, 230), (660, 540)], "color": (225, 235, 248)},
            {"type": "polygon", "points": [(640, 540), (900, 280), (1160, 540)], "color": (210, 225, 242)},
            # bông tuyết
            {"type": "ellipse", "box": [300, 120, 320, 140], "color": (255, 255, 255)},
            {"type": "ellipse", "box": [700, 80, 720, 100], "color": (255, 255, 255)},
            {"type": "ellipse", "box": [1000, 160, 1020, 180], "color": (255, 255, 255)},
        ],
    )

    print("Đã tạo 6 ảnh tại:", IMAGES_DIR)


# Mỗi câu tương ứng (theo ý nghĩa) với 1 ảnh ở trên — để dễ kiểm chứng kết quả ghép.
SCRIPT_SENTENCES = [
    "The golden sun slowly rises above the quiet mountain peaks.",
    "Gentle waves roll onto the warm sandy beach by the deep blue sea.",
    "Tall green trees fill the peaceful forest with fresh cool air.",
    "At night the city skyline glows with thousands of bright lights.",
    "Endless golden dunes stretch across the silent desert under the sun.",
    "Soft white snow covers the calm and frozen winter landscape.",
]


def make_voice_and_script():
    os.makedirs(INPUT_DIR, exist_ok=True)
    wav_path = os.path.join(INPUT_DIR, "voiceover.wav")
    script_path = os.path.join(INPUT_DIR, "script.txt")

    # Ghi script (mỗi câu một dòng)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write("\n".join(SCRIPT_SENTENCES))
    print("Đã tạo script tại:", script_path)

    # Tạo voiceover bằng Windows SAPI (đọc liền các câu, có nghỉ giữa câu)
    text = "  ".join(SCRIPT_SENTENCES)
    try:
        import comtypes.client

        engine = comtypes.client.CreateObject("SAPI.SpVoice")
        stream = comtypes.client.CreateObject("SAPI.SpFileStream")
        stream.Open(wav_path, 3)  # SSFMCreateForWrite
        engine.AudioOutputStream = stream
        engine.Rate = -2  # đọc chậm cho rõ
        engine.Speak(text)
        stream.Close()
        print("Đã tạo voiceover (SAPI) tại:", wav_path)
    except Exception as exc:
        print("Không tạo được voiceover bằng SAPI:", exc)
        print("Bạn có thể tự thu/ghi một file voiceover.wav vào thư mục sample_input.")
        return None, script_path

    return wav_path, script_path


def main():
    make_images()
    make_voice_and_script()
    print("\nXONG! Bộ input mẫu nằm trong:", INPUT_DIR)
    print("\nChạy thử tạo video (xuất ra thư mục riêng, không đụng CapCut):")
    print(
        '  .venv\\Scripts\\python.exe -m capcut_auto '
        '--images "sample_input\\images" '
        '--voiceover "sample_input\\voiceover.wav" '
        '--script "sample_input\\script.txt" '
        '--model-cache-dir "D:\\capcut_auto_models" '
        '--output-dir "sample_input\\out_draft"'
    )


if __name__ == "__main__":
    main()

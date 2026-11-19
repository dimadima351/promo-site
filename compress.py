"""
Стискання фото для сайту.

Як працює:
  1. Відкривається вікно вибору файлів (можна вибрати одне або багато фото).
  2. Кожне фото стискається.
  3. Стиснуте фото записується НА ТЕ САМЕ МІСЦЕ (з тією ж назвою),
     тож посилання на сайті не ламаються.
  4. Оригінал зберігається в папці _originals поруч (можна вимкнути).

Встановлення (один раз):
    pip install pillow

Запуск:
    python compress_photos.py
"""

import shutil
import sys
from pathlib import Path
from tkinter import Tk, filedialog, messagebox

from PIL import Image, ImageOps

# ---------------- НАЛАШТУВАННЯ ----------------
MAX_SIDE = 1600          # найбільша сторона фото в пікселях (більше буде зменшено)
JPEG_QUALITY = 80        # 70-85 оптимально: гарна якість, малий розмір
WEBP_QUALITY = 80
KEEP_BACKUP = True       # True = зберігати оригінал у папці _originals
BACKUP_DIR_NAME = "_originals"
# ----------------------------------------------

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}


def human(size: int) -> str:
    for unit in ("Б", "КБ", "МБ", "ГБ"):
        if size < 1024 or unit == "ГБ":
            return f"{size:.1f} {unit}" if unit != "Б" else f"{size} {unit}"
        size /= 1024
    return f"{size} Б"


def compress_one(path: Path) -> tuple[int, int, str]:
    """Повертає (розмір_до, розмір_після, статус)."""
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        return 0, 0, "пропущено (непідтримуваний формат)"

    original_size = path.stat().st_size
    tmp_path = path.with_name(path.stem + ".__tmp__" + path.suffix)

    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)  # виправляє поворот з телефону

        # зменшуємо, якщо завелике
        if max(img.size) > MAX_SIDE:
            img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)

        if ext in (".jpg", ".jpeg"):
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.save(tmp_path, "JPEG", quality=JPEG_QUALITY,
                     optimize=True, progressive=True)
        elif ext == ".png":
            img.save(tmp_path, "PNG", optimize=True)
        elif ext == ".webp":
            img.save(tmp_path, "WEBP", quality=WEBP_QUALITY, method=6)

    new_size = tmp_path.stat().st_size

    # якщо стиснуте вийшло не менше за оригінал, лишаємо оригінал
    if new_size >= original_size:
        tmp_path.unlink()
        return original_size, original_size, "вже оптимальне, не змінено"

    # резервна копія оригіналу
    if KEEP_BACKUP:
        backup_dir = path.parent / BACKUP_DIR_NAME
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / path.name
        if not backup_file.exists():  # не перезаписуємо найпершу копію
            shutil.copy2(path, backup_file)

    # підміна на тому ж місці з тією ж назвою
    tmp_path.replace(path)
    return original_size, new_size, "стиснуто"


def main() -> None:
    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    files = filedialog.askopenfilenames(
        title="Оберіть фото для стискання",
        filetypes=[("Зображення", "*.jpg *.jpeg *.png *.webp"),
                   ("Усі файли", "*.*")],
    )
    if not files:
        print("Нічого не вибрано.")
        return

    total_before = total_after = 0
    lines = []

    for f in files:
        path = Path(f)
        try:
            before, after, status = compress_one(path)
        except Exception as e:  # щоб одне зіпсоване фото не зупиняло все
            lines.append(f"✗ {path.name}: помилка ({e})")
            continue

        total_before += before
        total_after += after
        if before and before != after:
            saved = 100 - after * 100 / before
            lines.append(f"✓ {path.name}: {human(before)} → {human(after)} (−{saved:.0f}%)")
        else:
            lines.append(f"• {path.name}: {status}")

    saved_total = total_before - total_after
    summary = "\n".join(lines)
    summary += f"\n\nЗекономлено: {human(saved_total)}"
    if KEEP_BACKUP:
        summary += f"\nОригінали збережено в папці «{BACKUP_DIR_NAME}»."

    print(summary)
    messagebox.showinfo("Готово", summary)
    root.destroy()


if __name__ == "__main__":
    try:
        main()
    except ImportError:
        print("Встановіть Pillow: pip install pillow")
        sys.exit(1)
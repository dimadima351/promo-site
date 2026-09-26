#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Адмін-панель для керування подіями (з вертикальним скролом правої панелі).
Запуск: python3 admin_events.py
"""

import os
import sys
import json
import shutil
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from pathlib import Path
from PIL import Image

# ========== ШЛЯХИ ==========
BASE_DIR = Path(__file__).parent.resolve()
DATA_FILE = BASE_DIR / 'data' / 'events.json'
EVENTS_DIR = BASE_DIR / 'events'
EVENTS_DIR.mkdir(exist_ok=True)
DATA_FILE.parent.mkdir(exist_ok=True)


# ========== РОБОТА З ДАНИМИ ==========
def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'events' not in data:
                    data['events'] = []
                return data
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося прочитати JSON:\n{e}")
    return {"events": []}


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compress_image(src_path, dest_path, max_width=1600, quality=80):
    """Стискає фото до max_width, зберігає як JPG. Повертає розмір у КБ."""
    img = Image.open(src_path)
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)
    img.save(dest_path, 'JPEG', quality=quality, optimize=True)
    return os.path.getsize(dest_path) / 1024


def get_next_id(events):
    return max([ev.get('id', 0) for ev in events], default=0) + 1


def delete_event_folder(event_id):
    folder = EVENTS_DIR / str(event_id)
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)


def renumber_events(events):
    """Перенумеровує події та перейменовує папки 1, 2, 3..."""
    temp_map = {}

    for i, ev in enumerate(events, 1):
        old_id = ev.get('id')
        if old_id is None:
            continue
        old_folder = EVENTS_DIR / str(old_id)
        temp_folder = EVENTS_DIR / f"_tmp_{old_id}"
        if old_folder.exists() and old_folder != temp_folder:
            try:
                old_folder.rename(temp_folder)
                temp_map[old_id] = temp_folder
            except Exception as e:
                print(f"Не вдалося перейменувати {old_folder}: {e}")

    for i, ev in enumerate(events, 1):
        old_id = ev.get('id')
        new_id = i
        ev['id'] = new_id

        old_images = ev.get('images', [])
        new_images = []
        for img in old_images:
            parts = img.split('/')
            if len(parts) >= 4:
                filename = parts[-1]
                new_images.append(f"./events/{new_id}/{filename}")
            else:
                new_images.append(img)
        ev['images'] = new_images

        temp_folder = temp_map.get(old_id)
        new_folder = EVENTS_DIR / str(new_id)
        if temp_folder and temp_folder.exists():
            try:
                if new_folder.exists() and new_folder != temp_folder:
                    shutil.rmtree(new_folder, ignore_errors=True)
                temp_folder.rename(new_folder)
            except Exception as e:
                print(f"Не вдалося перейменувати {temp_folder} → {new_folder}: {e}")


# ========== GUI ==========
class EventsAdminApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Адмін-панель ПОДІЙ")
        self.root.geometry("1200x750")
        self.root.minsize(900, 600)

        self.data = load_data()
        self.editing_id = None
        self.new_photos = []

        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill='x')

        ttk.Label(top, text="🛠 Адмін-панель ПОДІЙ",
                  font=('', 14, 'bold')).pack(side='left')
        ttk.Button(top, text="🚀 Завантажити на сайт (git push)",
                   command=self.push_to_site).pack(side='right')

        ttk.Separator(self.root, orient='horizontal').pack(fill='x')

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill='both', expand=True)

        # ============================================================
        # ЛІВА ЧАСТИНА (таблиця)
        # ============================================================
        left = ttk.Frame(main)
        left.pack(side='left', fill='both', expand=True)

        ttk.Label(left, text="📋 Список подій",
                  font=('', 12, 'bold')).pack(anchor='w', pady=(0, 6))

        cols = ('id', 'title', 'eventDate', 'photos', 'link', 'visible')
        self.tree = ttk.Treeview(left, columns=cols, show='headings', height=25)

        self.tree.heading('id', text='№')
        self.tree.heading('title', text='Заголовок')
        self.tree.heading('eventDate', text='Дата події')
        self.tree.heading('photos', text='Фото')
        self.tree.heading('link', text='Лінк')
        self.tree.heading('visible', text='Показ')

        self.tree.column('id', width=40, anchor='center')
        self.tree.column('title', width=240)
        self.tree.column('eventDate', width=130, anchor='center')
        self.tree.column('photos', width=55, anchor='center')
        self.tree.column('link', width=55, anchor='center')
        self.tree.column('visible', width=55, anchor='center')

        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        btns = ttk.Frame(left)
        btns.pack(fill='x', pady=8)

        ttk.Button(btns, text="➕ Нова подія", command=self.new_event).pack(side='left', padx=2)
        ttk.Button(btns, text="✏️ Редагувати", command=self.edit_selected).pack(side='left', padx=2)
        ttk.Button(btns, text="🗑 Видалити", command=self.delete_selected).pack(side='left', padx=2)
        ttk.Button(btns, text="👁 Показати/Сховати", command=self.toggle_visibility).pack(side='left', padx=2)

        # ============================================================
        # ПРАВА ЧАСТИНА (форма) — З ВЕРТИКАЛЬНИМ СКРОЛОМ
        # ============================================================

        # Зовнішній контейнер фіксованої ширини
        right_outer = ttk.Frame(main)
        right_outer.pack(side='right', fill='y', padx=(15, 0))

        # Canvas + Scrollbar
        right_canvas = tk.Canvas(right_outer, width=470, highlightthickness=0, bd=0)
        right_scrollbar = ttk.Scrollbar(right_outer, orient='vertical', command=right_canvas.yview)
        right_canvas.configure(yscrollcommand=right_scrollbar.set)

        right_scrollbar.pack(side='right', fill='y')
        right_canvas.pack(side='left', fill='both', expand=True)

        # Внутрішній фрейм (форма) — усередині Canvas
        right = ttk.LabelFrame(right_canvas, text="Форма події", padding=10)
        right_window = right_canvas.create_window((0, 0), window=right, anchor='nw')

        # Оновлення scrollregion при зміні вмісту
        def _on_right_configure(event=None):
            right_canvas.configure(scrollregion=right_canvas.bbox('all'))

        right.bind('<Configure>', _on_right_configure)

        # Розтягування внутрішнього фрейму на ширину Canvas
        def _on_canvas_configure(event):
            right_canvas.itemconfig(right_window, width=event.width)

        right_canvas.bind('<Configure>', _on_canvas_configure)

        # Скрол коліщатком миші (тільки коли мишка над правою панеллю)
        def _on_mousewheel(event):
            if sys.platform == 'darwin':   # macOS
                right_canvas.yview_scroll(int(-1 * event.delta), 'units')
            else:                          # Windows / Linux
                right_canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        def _on_mousewheel_linux_up(event):
            right_canvas.yview_scroll(-1, 'units')

        def _on_mousewheel_linux_down(event):
            right_canvas.yview_scroll(1, 'units')

        def _bind_mousewheel(event):
            right_canvas.bind_all('<MouseWheel>', _on_mousewheel)
            right_canvas.bind_all('<Button-4>', _on_mousewheel_linux_up)
            right_canvas.bind_all('<Button-5>', _on_mousewheel_linux_down)

        def _unbind_mousewheel(event):
            right_canvas.unbind_all('<MouseWheel>')
            right_canvas.unbind_all('<Button-4>')
            right_canvas.unbind_all('<Button-5>')

        right_canvas.bind('<Enter>', _bind_mousewheel)
        right_canvas.bind('<Leave>', _unbind_mousewheel)

        # ============================================================
        # ФОРМА (як і раніше, усередині right)
        # ============================================================
        row = 0

        ttk.Label(right, text="Заголовок *").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_title = ttk.Entry(right, width=50)
        self.e_title.grid(row=row, column=0, pady=3, sticky='we')
        row += 1

        ttk.Label(right, text="Підзаголовок").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_subtitle = ttk.Entry(right, width=50)
        self.e_subtitle.grid(row=row, column=0, pady=3, sticky='we')
        row += 1

        ttk.Label(right, text="Адреса (не обов'язково)").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_address = ttk.Entry(right, width=50)
        self.e_address.grid(row=row, column=0, pady=3, sticky='we')
        row += 1

        ttk.Label(right, text="Дата публікації (РРРР-ММ-ДДTГГ:ХХ) *").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_published = ttk.Entry(right, width=50)
        self.e_published.grid(row=row, column=0, pady=3, sticky='we')
        self.e_published.insert(0, datetime.now().strftime('%Y-%m-%dT%H:%M'))
        row += 1

        ttk.Label(right, text="Дата події (РРРР-ММ-ДДTГГ:ХХ)").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_eventdate = ttk.Entry(right, width=50)
        self.e_eventdate.grid(row=row, column=0, pady=3, sticky='we')
        row += 1

        ttk.Label(right, text="Опис").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.t_description = tk.Text(right, width=50, height=5, wrap='word')
        self.t_description.grid(row=row, column=0, pady=3, sticky='we')
        row += 1

        # === БЛОК ЛІНКА ===
        ttk.Separator(right, orient='horizontal').grid(row=row, column=0, sticky='we', pady=8)
        row += 1

        ttk.Label(right, text="🔗 Кнопка-лінк (не обов'язково)",
                  font=('', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=(0, 4))
        row += 1

        ttk.Label(right, text="Текст над кнопкою (підпис)").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_linklabel = ttk.Entry(right, width=50)
        self.e_linklabel.grid(row=row, column=0, pady=3, sticky='we')
        row += 1

        ttk.Label(right, text="Текст на кнопці").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_linktext = ttk.Entry(right, width=50)
        self.e_linktext.grid(row=row, column=0, pady=3, sticky='we')
        self.e_linktext.insert(0, "Перейти")
        row += 1

        ttk.Label(right, text="URL куди веде кнопка (https://...)").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_linkurl = ttk.Entry(right, width=50)
        self.e_linkurl.grid(row=row, column=0, pady=3, sticky='we')
        row += 1

        # === ФОТО ===
        ttk.Separator(right, orient='horizontal').grid(row=row, column=0, sticky='we', pady=8)
        row += 1

        ttk.Label(right, text="📷 Фотографії (виберіть декілька)").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        photo_frame = ttk.Frame(right)
        photo_frame.grid(row=row, column=0, pady=3, sticky='we')
        ttk.Button(photo_frame, text="📷 Додати фото", command=self.choose_photos).pack(side='left')
        self.lbl_photos = ttk.Label(photo_frame, text="0 фото", foreground='#777')
        self.lbl_photos.pack(side='left', padx=8)
        row += 1

        self.lb_photos = tk.Listbox(right, height=3, width=50)
        self.lb_photos.grid(row=row, column=0, pady=3, sticky='we')
        row += 1

        # === ВИДИМІСТЬ ===
        self.var_visible = tk.BooleanVar(value=True)
        ttk.Checkbutton(right, text="✅ Показувати на сайті",
                        variable=self.var_visible).grid(row=row, column=0, sticky='w', pady=3)
        row += 1

        # === КНОПКИ ФОРМИ ===
        form_btns = ttk.Frame(right)
        form_btns.grid(row=row, column=0, pady=15, sticky='we')
        self.btn_save = ttk.Button(form_btns, text="💾 Зберегти подію", command=self.save_event)
        self.btn_save.pack(side='left', padx=2)
        ttk.Button(form_btns, text="🔄 Очистити", command=self.clear_form).pack(side='left', padx=2)

    # ---------- Таблиця ----------
    def _refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for ev in self.data['events']:
            visible = '✅' if ev.get('visible', True) else '❌'
            photos_count = len(ev.get('images', []))
            has_link = '🔗' if ev.get('linkUrl') else ''
            event_date = ev.get('eventDate', '') or ev.get('publishedAt', '')
            self.tree.insert('', 'end', iid=str(ev['id']),
                             values=(ev['id'], ev['title'],
                                     event_date.replace('T', ' '),
                                     photos_count, has_link, visible))

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        self.edit_selected()

    # ---------- Форма: очищення ----------
    def clear_form(self):
        self.editing_id = None
        self.new_photos = []
        self.e_title.delete(0, 'end')
        self.e_subtitle.delete(0, 'end')
        self.e_address.delete(0, 'end')
        self.e_published.delete(0, 'end')
        self.e_published.insert(0, datetime.now().strftime('%Y-%m-%dT%H:%M'))
        self.e_eventdate.delete(0, 'end')
        self.t_description.delete('1.0', 'end')

        self.e_linklabel.delete(0, 'end')
        self.e_linktext.delete(0, 'end')
        self.e_linktext.insert(0, "Перейти")
        self.e_linkurl.delete(0, 'end')

        self.lb_photos.delete(0, 'end')
        self.lbl_photos.config(text="0 фото", foreground='#777')
        self.var_visible.set(True)
        self.btn_save.config(text="💾 Зберегти подію")

    def new_event(self):
        self.clear_form()

    # ---------- Заповнення форми ----------
    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Інфо", "Виберіть подію у списку")
            return
        ev_id = int(sel[0])
        ev = next((e for e in self.data['events'] if e['id'] == ev_id), None)
        if not ev:
            return

        self.editing_id = ev_id
        self.new_photos = []

        self.e_title.delete(0, 'end'); self.e_title.insert(0, ev.get('title', ''))
        self.e_subtitle.delete(0, 'end'); self.e_subtitle.insert(0, ev.get('subtitle', ''))
        self.e_address.delete(0, 'end'); self.e_address.insert(0, ev.get('address', ''))
        self.e_published.delete(0, 'end'); self.e_published.insert(0, ev.get('publishedAt', ''))
        self.e_eventdate.delete(0, 'end'); self.e_eventdate.insert(0, ev.get('eventDate', ''))

        self.t_description.delete('1.0', 'end')
        self.t_description.insert('1.0', ev.get('description', ''))

        self.e_linklabel.delete(0, 'end')
        self.e_linklabel.insert(0, ev.get('linkLabel', ''))
        self.e_linktext.delete(0, 'end')
        self.e_linktext.insert(0, ev.get('linkText', 'Перейти'))
        self.e_linkurl.delete(0, 'end')
        self.e_linkurl.insert(0, ev.get('linkUrl', ''))

        self.lb_photos.delete(0, 'end')
        for img in ev.get('images', []):
            self.lb_photos.insert('end', img)
        self.lbl_photos.config(text=f"{len(ev.get('images', []))} фото", foreground='#555')

        self.var_visible.set(ev.get('visible', True))
        self.btn_save.config(text="💾 Оновити подію")

    # ---------- Вибір фото ----------
    def choose_photos(self):
        paths = filedialog.askopenfilenames(
            title="Виберіть фотографії",
            filetypes=[("Зображення", "*.jpg *.jpeg *.png *.webp *.bmp")]
        )
        if not paths:
            return
        for p in paths:
            self.new_photos.append(p)
            self.lb_photos.insert('end', f"[НОВЕ] {p}")

        total = self.lb_photos.size()
        self.lbl_photos.config(text=f"{total} фото (з них {len(self.new_photos)} нових)",
                               foreground='#555')

    # ---------- Збереження ----------
    def save_event(self):
        title = self.e_title.get().strip()
        if not title:
            messagebox.showerror("Помилка", "Введіть заголовок події")
            return

        published = self.e_published.get().strip()
        if not published:
            messagebox.showerror("Помилка", "Введіть дату публікації")
            return

        link_url = self.e_linkurl.get().strip()
        if link_url and not (link_url.startswith('http://') or link_url.startswith('https://')):
            if not messagebox.askyesno("Підтвердження",
                                       "URL не починається з http:// або https://.\nПродовжити?"):
                return

        if self.editing_id is None:
            new_id = get_next_id(self.data['events'])
            folder = EVENTS_DIR / str(new_id)
        else:
            new_id = self.editing_id
            folder = EVENTS_DIR / str(new_id)

        folder.mkdir(exist_ok=True)

        images = []

        if self.editing_id is not None:
            ev = next((e for e in self.data['events'] if e['id'] == self.editing_id), None)
            if ev:
                for i in range(self.lb_photos.size()):
                    item = self.lb_photos.get(i)
                    if not item.startswith('[НОВЕ]'):
                        images.append(item)

        max_num = 0
        for img in images:
            try:
                fname = Path(img).name
                num = int(fname.split('.')[0])
                if num > max_num:
                    max_num = num
            except Exception:
                pass

        for src in self.new_photos:
            max_num += 1
            fname = f"{max_num}.jpg"
            dest = folder / fname
            try:
                compress_image(src, dest)
                images.append(f"./events/{new_id}/{fname}")
            except Exception as e:
                messagebox.showerror("Помилка фото", f"{src}\n{e}")
                return

        if not images:
            messagebox.showerror("Помилка", "Додайте хоча б одне фото")
            return

        ev_data = {
            "id": new_id,
            "title": title,
            "subtitle": self.e_subtitle.get().strip(),
            "address": self.e_address.get().strip(),
            "publishedAt": published,
            "eventDate": self.e_eventdate.get().strip(),
            "description": self.t_description.get('1.0', 'end').strip(),
            "images": images,
            "linkLabel": self.e_linklabel.get().strip(),
            "linkText": self.e_linktext.get().strip() or "Перейти",
            "linkUrl": link_url,
            "visible": self.var_visible.get()
        }

        if self.editing_id is None:
            self.data['events'].append(ev_data)
        else:
            for i, e in enumerate(self.data['events']):
                if e['id'] == self.editing_id:
                    self.data['events'][i] = ev_data
                    break

        save_data(self.data)
        self._refresh_table()
        self.clear_form()
        messagebox.showinfo("Готово", f"Подію «{title}» збережено ✅")

    # ---------- Видалення ----------
    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Інфо", "Виберіть подію")
            return
        ev_id = int(sel[0])
        ev = next((e for e in self.data['events'] if e['id'] == ev_id), None)
        if not ev:
            return
        if not messagebox.askyesno("Підтвердження", f"Видалити «{ev['title']}»?"):
            return

        delete_event_folder(ev_id)
        self.data['events'].remove(ev)
        renumber_events(self.data['events'])
        save_data(self.data)
        self._refresh_table()
        self.clear_form()

    # ---------- Видимість ----------
    def toggle_visibility(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Інфо", "Виберіть подію")
            return
        ev_id = int(sel[0])
        for ev in self.data['events']:
            if ev['id'] == ev_id:
                ev['visible'] = not ev.get('visible', True)
                break
        save_data(self.data)
        self._refresh_table()
        self.tree.selection_set(str(ev_id))

    # ---------- Git push ----------
    def push_to_site(self):
        if not messagebox.askyesno("Підтвердження", "Завантажити зміни на GitHub?"):
            return
        try:
            save_data(self.data)
            subprocess.run(['git', 'add', '.'], cwd=BASE_DIR, check=True)
            msg = f"Оновлено події {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            r = subprocess.run(['git', 'commit', '-m', msg],
                               cwd=BASE_DIR, capture_output=True, text=True)
            if r.returncode != 0 and 'nothing to commit' not in (r.stdout + r.stderr):
                messagebox.showerror("Git commit", r.stderr or r.stdout)
                return
            subprocess.run(['git', 'push'], cwd=BASE_DIR, check=True)
            messagebox.showinfo("Готово", "✅ Завантажено на сайт!\n\nЧерез 1-2 хвилини з'явиться.")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Git помилка", str(e))


# ========== ЗАПУСК ==========
if __name__ == '__main__':
    root = tk.Tk()
    app = EventsAdminApp(root)
    root.mainloop()
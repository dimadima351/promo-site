#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Адмін-панель PromoSite — GUI-застосунок.
Запуск: python3 admin.py
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
DATA_FILE = BASE_DIR / 'data' / 'promotions.json'
IMAGES_DIR = BASE_DIR / 'images'
IMAGES_DIR.mkdir(exist_ok=True)
DATA_FILE.parent.mkdir(exist_ok=True)

CATEGORIES = [
    "Молочні продукти", "М'ясні вироби", "Риба та морепродукти", "Яйця",
    "Хліб та випічка", "Солодощі", "Фрукти та овочі", "Консервація",
    "Бакалія", "Горіхи та сухофрукти", "Соуси та приправи",
    "Безалкогольні напої", "Кава та чай", "Алкоголь", "Заморожені продукти",
    "Напівфабрикати", "Готові страви", "Соління та маринади", "Олія",
    "Дитяче харчування", "Здорове харчування", "Товари для тварин",
    "Побутова хімія", "Товари для дому", "Засоби гігієни"
]


# ========== РОБОТА З ДАНИМИ ==========
def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося прочитати JSON:\n{e}")
    return {"month": "", "items": []}


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def compress_image(src_path, dest_path, max_width=600, quality=75):
    """Стискає картинку → JPG. Повертає розмір у КБ."""
    img = Image.open(src_path)
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)
    img.save(dest_path, 'JPEG', quality=quality, optimize=True)
    return os.path.getsize(dest_path) / 1024


def get_next_id(items):
    return max([it.get('id', 0) for it in items], default=0) + 1


def renumber_items(items):
    """Перенумеровує товари 1, 2, 3... і перейменовує їхні картинки."""
    for i, it in enumerate(items, 1):
        old_path = BASE_DIR / it['image'].lstrip('./')
        new_name = f"{i}.jpg"
        new_path = IMAGES_DIR / new_name
        if old_path.exists() and old_path.resolve() != new_path.resolve():
            try:
                if new_path.exists():
                    new_path.unlink()
                old_path.rename(new_path)
            except Exception:
                pass
        it['id'] = i
        it['image'] = f"./images/{new_name}"


# ========== GUI ==========
class AdminApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Адмін-панель PromoSite")
        self.root.geometry("1100x700")
        self.root.minsize(900, 600)

        self.data = load_data()
        self.editing_id = None       # ID товару, який зараз редагуємо
        self.current_image_src = None  # шлях до вибраної картинки

        self._build_ui()
        self._refresh_table()

    # ---------- Побудова інтерфейсу ----------
    def _build_ui(self):
        # Верхня панель з назвою місяця + кнопкою пуш
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill='x')

        ttk.Label(top, text="Місяць:").pack(side='left')
        self.month_var = tk.StringVar(value=self.data.get('month', ''))
        ttk.Entry(top, textvariable=self.month_var, width=25).pack(side='left', padx=5)

        ttk.Button(top, text="💾 Зберегти місяць",
                   command=self.save_month).pack(side='left', padx=5)

        ttk.Button(top, text="🚀 Завантажити на сайт (git push)",
                   command=self.push_to_site).pack(side='right')

        # Розділювач
        ttk.Separator(self.root, orient='horizontal').pack(fill='x')

        # Основна частина: список зліва, форма справа
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill='both', expand=True)

        # === ЛІВА ЧАСТИНА: таблиця ===
        left = ttk.Frame(main)
        left.pack(side='left', fill='both', expand=True)

        ttk.Label(left, text="📋 Список товарів",
                  font=('', 12, 'bold')).pack(anchor='w')

        cols = ('id', 'name', 'category', 'price', 'visible')
        self.tree = ttk.Treeview(left, columns=cols, show='headings', height=25)
        self.tree.heading('id', text='№')
        self.tree.heading('name', text='Назва')
        self.tree.heading('category', text='Категорія')
        self.tree.heading('price', text='Ціна')
        self.tree.heading('visible', text='Показ')

        self.tree.column('id', width=40, anchor='center')
        self.tree.column('name', width=200)
        self.tree.column('category', width=160)
        self.tree.column('price', width=80, anchor='e')
        self.tree.column('visible', width=60, anchor='center')

        self.tree.pack(fill='both', expand=True, pady=5)
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # Кнопки під таблицею
        btns = ttk.Frame(left)
        btns.pack(fill='x', pady=5)

        ttk.Button(btns, text="➕ Новий товар",
                   command=self.new_item).pack(side='left', padx=2)
        ttk.Button(btns, text="✏️ Редагувати",
                   command=self.edit_selected).pack(side='left', padx=2)
        ttk.Button(btns, text="🗑 Видалити",
                   command=self.delete_selected).pack(side='left', padx=2)
        ttk.Button(btns, text="👁 Показати/Сховати",
                   command=self.toggle_visibility).pack(side='left', padx=2)

        # === ПРАВА ЧАСТИНА: форма ===
        right = ttk.LabelFrame(main, text="Форма товару", padding=10)
        right.pack(side='right', fill='y', padx=(15, 0))
        right.configure(width=380)

        row = 0
        # Назва
        ttk.Label(right, text="Назва *").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_name = ttk.Entry(right, width=35)
        self.e_name.grid(row=row, column=0, pady=3, sticky='we')
        row += 1

        # Виробник
        ttk.Label(right, text="Виробник").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_manufacturer = ttk.Entry(right, width=35)
        self.e_manufacturer.grid(row=row, column=0, pady=3, sticky='we')
        row += 1

        # Категорія
        ttk.Label(right, text="Категорія *").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.cb_category = ttk.Combobox(right, values=CATEGORIES, width=33)
        self.cb_category.grid(row=row, column=0, pady=3, sticky='we')
        row += 1

        # Ціна
        ttk.Label(right, text="Ціна (грн) *").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_price = ttk.Entry(right, width=35)
        self.e_price.grid(row=row, column=0, pady=3, sticky='we')
        self.e_price.bind('<KeyRelease>', self._update_discount_preview)
        row += 1

        # Стара ціна (галочка)
        self.var_discount = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, text="Є акційна ціна (стара ціна)",
                        variable=self.var_discount,
                        command=self._toggle_discount).grid(row=row, column=0, sticky='w', pady=3)
        row += 1

        self.lbl_old_price = ttk.Label(right, text="Стара ціна (грн)")
        self.lbl_old_price.grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_old_price = ttk.Entry(right, width=35, state='disabled')
        self.e_old_price.grid(row=row, column=0, pady=3, sticky='we')
        self.e_old_price.bind('<KeyRelease>', self._update_discount_preview)
        row += 1

        self.lbl_discount = ttk.Label(right, text="Знижка: —", foreground='#ff0b0b')
        self.lbl_discount.grid(row=row, column=0, sticky='w', pady=3)
        row += 1

        # Акція діє до
        ttk.Label(right, text="Акція діє до (ДД.ММ.РРРР)").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        self.e_valid_until = ttk.Entry(right, width=35)
        self.e_valid_until.grid(row=row, column=0, pady=3, sticky='we')
        row += 1

        # Картинка
        ttk.Label(right, text="Картинка *").grid(row=row, column=0, sticky='w', pady=3)
        row += 1
        img_frame = ttk.Frame(right)
        img_frame.grid(row=row, column=0, pady=3, sticky='we')
        self.btn_image = ttk.Button(img_frame, text="📷 Вибрати фото",
                                    command=self.choose_image)
        self.btn_image.pack(side='left')
        self.lbl_image = ttk.Label(img_frame, text="не вибрано", foreground='#777')
        self.lbl_image.pack(side='left', padx=8)
        row += 1

        # Галочки
        self.var_is_action = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, text="Акція", variable=self.var_is_action)\
            .grid(row=row, column=0, sticky='w', pady=3)
        row += 1

        self.var_is_month = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, text="Акція місяця (зверху списку)",
                        variable=self.var_is_month)\
            .grid(row=row, column=0, sticky='w', pady=3)
        row += 1

        self.var_visible = tk.BooleanVar(value=True)
        ttk.Checkbutton(right, text="✅ Показувати на сайті",
                        variable=self.var_visible)\
            .grid(row=row, column=0, sticky='w', pady=3)
        row += 1

        # Кнопки форми
        form_btns = ttk.Frame(right)
        form_btns.grid(row=row, column=0, pady=15, sticky='we')
        self.btn_save = ttk.Button(form_btns, text="💾 Зберегти товар",
                                   command=self.save_item)
        self.btn_save.pack(side='left', padx=2)
        ttk.Button(form_btns, text="🔄 Очистити",
                   command=self.clear_form).pack(side='left', padx=2)

    # ---------- Оновлення таблиці ----------
    def _refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for it in self.data['items']:
            visible = '✅' if it.get('visible', True) else '❌'
            self.tree.insert('', 'end', iid=str(it['id']),
                             values=(it['id'], it['name'],
                                     it.get('category', ''),
                                     f"{it['price']} ₴", visible))

    # ---------- Вибір товару ----------
    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item_id = int(sel[0])
        self.edit_selected()

    # ---------- Форма: очищення ----------
    def clear_form(self):
        self.editing_id = None
        self.current_image_src = None
        self.e_name.delete(0, 'end')
        self.e_manufacturer.delete(0, 'end')
        self.cb_category.set('')
        self.e_price.delete(0, 'end')
        self.e_old_price.delete(0, 'end')
        self.e_valid_until.delete(0, 'end')
        self.var_discount.set(False)
        self.var_is_action.set(False)
        self.var_is_month.set(False)
        self.var_visible.set(True)
        self._toggle_discount()
        self.lbl_image.config(text="не вибрано", foreground='#777')
        self.btn_save.config(text="💾 Зберегти товар")

    # ---------- Форма: нова позиція ----------
    def new_item(self):
        self.clear_form()

    # ---------- Форма: заповнення з товару ----------
    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Інфо", "Виберіть товар у списку")
            return
        item_id = int(sel[0])
        item = next((it for it in self.data['items'] if it['id'] == item_id), None)
        if not item:
            return

        self.editing_id = item_id
        self.current_image_src = None

        self.e_name.delete(0, 'end'); self.e_name.insert(0, item.get('name', ''))
        self.e_manufacturer.delete(0, 'end')
        self.e_manufacturer.insert(0, item.get('manufacturer', ''))
        self.cb_category.set(item.get('category', ''))
        self.e_price.delete(0, 'end')
        self.e_price.insert(0, str(item.get('price', '')))

        old_price = item.get('oldPrice')
        self.var_discount.set(bool(old_price))
        self.e_old_price.delete(0, 'end')
        if old_price:
            self.e_old_price.insert(0, str(old_price))
        self._toggle_discount()
        self._update_discount_preview()

        self.e_valid_until.delete(0, 'end')
        self.e_valid_until.insert(0, item.get('validUntil', ''))

        self.var_is_action.set(item.get('isAction', False))
        self.var_is_month.set(item.get('isMonthAction', False))
        self.var_visible.set(item.get('visible', True))

        # Інформація про картинку
        img_file = Path(item['image']).name
        exists = (IMAGES_DIR / img_file).exists()
        self.lbl_image.config(
            text=f"{img_file}" + ("" if exists else " (файл відсутній)"),
            foreground='#555' if exists else '#ff0b0b'
        )
        self.btn_save.config(text="💾 Оновити товар")

    # ---------- Перемикач галочки старої ціни ----------
    def _toggle_discount(self):
        if self.var_discount.get():
            self.e_old_price.config(state='normal')
            self.lbl_old_price.config(foreground='#000')
        else:
            self.e_old_price.config(state='disabled')
            self.lbl_old_price.config(foreground='#888')
            self.e_old_price.delete(0, 'end')
        self._update_discount_preview()

    # ---------- Автоматична знижка ----------
    def _update_discount_preview(self, event=None):
        try:
            price = float(self.e_price.get().replace(',', '.'))
        except ValueError:
            price = 0
        try:
            old = float(self.e_old_price.get().replace(',', '.'))
        except ValueError:
            old = 0

        if old > price > 0:
            percent = round((1 - price / old) * 100)
            self.lbl_discount.config(text=f"Знижка: -{percent}%")
        else:
            self.lbl_discount.config(text="Знижка: —")

    # ---------- Вибір картинки ----------
    def choose_image(self):
        path = filedialog.askopenfilename(
            title="Виберіть картинку",
            filetypes=[("Зображення", "*.jpg *.jpeg *.png *.webp *.bmp")]
        )
        if path:
            self.current_image_src = path
            self.lbl_image.config(text=Path(path).name, foreground='#555')

    # ---------- Збереження товару ----------
    def save_item(self):
        name = self.e_name.get().strip()
        if not name:
            messagebox.showerror("Помилка", "Введіть назву товару")
            return

        try:
            price = float(self.e_price.get().replace(',', '.'))
            if price <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Помилка", "Введіть коректну ціну")
            return

        has_discount = self.var_discount.get()
        old_price = None
        badge = None
        if has_discount:
            try:
                old_price = float(self.e_old_price.get().replace(',', '.'))
                if old_price <= price:
                    raise ValueError
                badge = f"-{round((1 - price / old_price) * 100)}%"
            except ValueError:
                messagebox.showerror("Помилка",
                                     "Стара ціна має бути більшою за нову")
                return

        # Нова позиція чи редагування?
        if self.editing_id is None:
            new_id = get_next_id(self.data['items'])
            file_name = f"{new_id}.jpg"
            if not self.current_image_src:
                messagebox.showerror("Помилка", "Виберіть картинку")
                return
        else:
            item = next((it for it in self.data['items']
                         if it['id'] == self.editing_id), None)
            if not item:
                return
            new_id = self.editing_id
            file_name = Path(item['image']).name
            if self.current_image_src:
                # Замінюємо картинку
                file_name = f"{new_id}.jpg"

        # Стискаємо картинку (якщо вибрано нову)
        if self.current_image_src:
            try:
                size_kb = compress_image(
                    self.current_image_src,
                    IMAGES_DIR / file_name
                )
            except Exception as e:
                messagebox.showerror("Помилка картинки", str(e))
                return

        item_data = {
            "id": new_id,
            "name": name,
            "manufacturer": self.e_manufacturer.get().strip(),
            "category": self.cb_category.get().strip(),
            "price": price,
            "oldPrice": old_price,
            "badge": badge,
            "image": f"./images/{file_name}",
            "link": "#",
            "validUntil": self.e_valid_until.get().strip(),
            "isAction": self.var_is_action.get(),
            "isMonthAction": self.var_is_month.get(),
            "visible": self.var_visible.get()
        }

        if self.editing_id is None:
            self.data['items'].append(item_data)
        else:
            for i, it in enumerate(self.data['items']):
                if it['id'] == self.editing_id:
                    self.data['items'][i] = item_data
                    break

        # Автозбереження JSON
        save_data(self.data)

        self._refresh_table()
        self.clear_form()
        messagebox.showinfo("Готово", f"Товар '{name}' збережено ✅")

    # ---------- Видалення ----------
    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Інфо", "Виберіть товар")
            return
        item_id = int(sel[0])
        item = next((it for it in self.data['items'] if it['id'] == item_id), None)
        if not item:
            return
        if not messagebox.askyesno("Підтвердження",
                                   f"Видалити '{item['name']}'?"):
            return

        img = BASE_DIR / item['image'].lstrip('./')
        if img.exists():
            img.unlink()

        self.data['items'].remove(item)
        renumber_items(self.data['items'])
        save_data(self.data)
        self._refresh_table()
        self.clear_form()

    # ---------- Перемикач видимості ----------
    def toggle_visibility(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Інфо", "Виберіть товар")
            return
        item_id = int(sel[0])
        for it in self.data['items']:
            if it['id'] == item_id:
                it['visible'] = not it.get('visible', True)
                break
        save_data(self.data)
        self._refresh_table()
        # Зберігаємо виділення
        self.tree.selection_set(str(item_id))

    # ---------- Збереження місяця ----------
    def save_month(self):
        self.data['month'] = self.month_var.get().strip()
        save_data(self.data)
        messagebox.showinfo("Готово", "Місяць збережено ✅")

    # ---------- Git push ----------
    def push_to_site(self):
        if not messagebox.askyesno("Підтвердження",
                                   "Завантажити зміни на GitHub?"):
            return
        try:
            save_data(self.data)
            subprocess.run(['git', 'add', '.'], cwd=BASE_DIR, check=True)
            msg = f"Оновлено акції {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            subprocess.run(['git', 'commit', '-m', msg],
                           cwd=BASE_DIR, check=True, capture_output=True)
            subprocess.run(['git', 'push'], cwd=BASE_DIR, check=True)
            messagebox.showinfo("Готово",
                                "✅ Завантажено на сайт!\n\n"
                                "Через 1-2 хвилини зміни з'являться.")
        except subprocess.CalledProcessError as e:
            msg = e.stderr.decode() if e.stderr else str(e)
            messagebox.showerror("Git помилка", msg)


# ========== ЗАПУСК ==========
if __name__ == '__main__':
    root = tk.Tk()
    app = AdminApp(root)
    root.mainloop()

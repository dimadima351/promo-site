#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import io
import re
import requests
from PIL import Image, ImageTk
from ddgs import DDGS

class ImageFinderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Пошук чистих картинок товарів")
        self.root.geometry("950x700")
        self.root.configure(bg="#f0f0f0")

        # Сайти, з яких НЕ беремо картинки (бо там водяні знаки)
        self.bad_domains = [
            'epicentr', 'rozetka', 'prom.ua', 'olx', 'aliexpress', 
            'amazon', 'ebay', 'shafa', 'leroymerlin', 'foxtrot', 
            'comfy', 'ct.ua', 'moyo', 'modna-kasta', 'silpo', 'atb', 'novus'
        ]

        self._build_ui()

    def _build_ui(self):
        top_frame = tk.Frame(self.root, bg="#f0f0f0", pady=15, padx=15)
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="Назва товару:", font=("Arial", 14), bg="#f0f0f0").pack(side=tk.LEFT, padx=(0, 10))

        # Поле введення
        self.query_entry = tk.Entry(top_frame, font=("Arial", 14), width=40)
        self.query_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.query_entry.bind("<Return>", lambda e: self.start_search())

        self.search_btn = tk.Button(top_frame, text="🔍 Шукати", font=("Arial", 12, "bold"), bg="#ff0b0b", fg="white", command=self.start_search)
        self.search_btn.pack(side=tk.LEFT)

        self.status_lbl = tk.Label(top_frame, text="", bg="#f0f0f0", fg="#555", font=("Arial", 11))
        self.status_lbl.pack(side=tk.LEFT, padx=20)

        # Скрол
        self.canvas = tk.Canvas(self.root, bg="#f0f0f0")
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#f0f0f0")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True, padx=10)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

    def clean_query(self, raw_query):
        """
        Розумна обробка запиту.
        Якщо є текст у лапках «...», беремо тільки його.
        Інакше прибираємо зайві слова (об'єм, опис).
        """
        # 1. Шукаємо текст у лапках «...» або "..."
        match = re.search(r'[«"](.*?)[»"]', raw_query)
        if match:
            return match.group(1).strip()

        # 2. Якщо лапок немає, прибираємо типові слова-сміття
        stop_words = [
            r'\bнапій\b', r'\bб/а\b', r'\bенергетичний\b', r'\bсоковий\b', 
            r'\bсеред/газ\b', r'\bбан\.?\s*\d+[\.,]?\d*\s*л\b', r'\bпляшка\b', 
            r'\bскло\b', r'\bбанка\b', r'\b\d+[\.,]?\d*\s*л\b'
        ]
        cleaned = raw_query
        for word in stop_words:
            cleaned = re.sub(word, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()

    def start_search(self):
        raw_query = self.query_entry.get().strip()
        if not raw_query:
            messagebox.showwarning("Увага", "Введіть назву товару!")
            return

        # Очищаємо запит
        clean_q = self.clean_query(raw_query)
        if not clean_q:
            clean_q = raw_query # Якщо все видалилось, беремо оригінал

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.status_lbl.config(text=f"Шукаю: «{clean_q}»... ⏳")
        self.search_btn.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=self._search_and_download, args=(clean_q,))
        thread.daemon = True
        thread.start()

    def _search_and_download(self, query):
        # Беремо назву в лапки, щоб пошуковик шукав точний збіг
        search_query = f'"{query}" product'
        
        images_found = 0
        valid_images = 0

        try:
            with DDGS() as ddgs:
                results = list(ddgs.images(search_query, max_results=100))

            if not results:
                # Якщо точний збіг нічого не дав, шукаємо без лапок
                with DDGS() as ddgs:
                    results = list(ddgs.images(f'{query} product white background', max_results=100))

            for res in results:
                if valid_images >= 15:
                    break
                
                img_url = res.get("image", "")
                if not img_url: continue

                # ФІЛЬТР 1: Домени-смітники
                if any(bad in img_url.lower() for bad in self.bad_domains):
                    continue

                images_found += 1
                self.root.after(0, lambda f=images_found: self.status_lbl.config(text=f"Перевірка {f}..."))

                try:
                    # ФІЛЬТР 2: Завантаження та розмір
                    resp = requests.get(img_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                    if resp.status_code != 200: continue
                    
                    img_data = io.BytesIO(resp.content)
                    img = Image.open(img_data)
                    img.load()

                    if img.width < 350 or img.height < 350: continue

                    # ФІЛЬТР 3: Білий фон
                    if self._is_white_background(img):
                        valid_images += 1
                        self.root.after(0, lambda i=img, u=img_url: self._add_image_to_ui(i, u))
                        
                except Exception:
                    pass

            self.root.after(0, lambda: self.status_lbl.config(text=f"Готово. Знайдено: {valid_images}"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Помилка", f"Помилка пошуку: {e}"))
            self.root.after(0, lambda: self.status_lbl.config(text="Помилка"))
        finally:
            self.root.after(0, lambda: self.search_btn.config(state=tk.NORMAL))

    def _is_white_background(self, img):
        if img.mode in ('RGBA', 'LA', 'P'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')
            
        w, h = img.size
        cw, ch = int(w * 0.15), int(h * 0.15)
        
        corners = [
            img.crop((0, 0, cw, ch)), 
            img.crop((w-cw, 0, w, ch)), 
            img.crop((0, h-ch, cw, h)), 
            img.crop((w-cw, h-ch, w, h)) 
        ]
        
        white_corners = 0
        for corner in corners:
            gray = corner.convert('L')
            pixels = list(gray.getdata())
            if sum(pixels) / len(pixels) > 210: # Трохи зменшив поріг для кращої роботи з тінями
                white_corners += 1
                
        return white_corners >= 3 

    def _add_image_to_ui(self, pil_img, url):
        display_img = pil_img.copy()
        display_img.thumbnail((250, 250), Image.LANCZOS)
        tk_img = ImageTk.PhotoImage(display_img)

        frame = tk.Frame(self.scrollable_frame, bg="white", bd=2, relief=tk.RIDGE)
        frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)

        lbl = tk.Label(frame, image=tk_img, bg="white")
        lbl.image = tk_img
        lbl.pack(pady=5)

        # Змінив емодзі на звичайний текст, щоб не було квадратиків на macOS
        btn = tk.Button(frame, text="Зберегти", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"),
                        command=lambda i=pil_img: self.save_image(i))
        btn.pack(pady=(0, 10), fill=tk.X, padx=10)

    def save_image(self, pil_img):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".jpg",
                filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")],
                initialdir="./images",
                initialfile="product_clean.jpg"
            )
            if filename:
                if pil_img.mode in ('RGBA', 'LA', 'P'):
                    bg = Image.new('RGB', pil_img.size, (255, 255, 255))
                    bg.paste(pil_img, mask=pil_img.split()[-1])
                    pil_img = bg
                pil_img.save(filename, quality=95)
                messagebox.showinfo("Успіх", "Картинку збережено!")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageFinderApp(root)
    root.mainloop()
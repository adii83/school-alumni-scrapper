import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import queue
import sys
import os
import time
import json
import pandas as pd
from core.api_manager import ApiKeyManager
from core.apify_service import panggil_apify, proses_hasil
from utils.name_utils import pisahkan_nama
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
class StdoutRedirector:
    def __init__(self, q):
        self.q = q
    def write(self, text):
        if text:
            self.q.put(text)
    def flush(self):
        pass
class ScraperApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Alumni Scrapper")
        self.minsize(1200, 720)
        self.configure(fg_color="#090B12")
        self.after(120, self._open_maximized)
        self._true_fullscreen = False
        self.bind("<F11>", self._toggle_true_fullscreen)
        self.bind("<Escape>", self._exit_true_fullscreen)
        self.excel_path = ctk.StringVar()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.is_running = False
        self.key_mgr = None
        self._processed = 0
        self._saved = 0
        self._skipped = 0
        self._total = 0
        self.log_q = queue.Queue()
        self._api_keys = []
        self._key_rows = []
        self._load_keys()
        self._old_stdout = sys.stdout
        sys.stdout = StdoutRedirector(self.log_q)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._build_ui()
        self._rebuild_key_mgr()
        self._poll_log()
        self._log("[INFO] Alumni Scrapper siap digunakan.\n")
        self._log("[INFO] Tambahkan API Key, pilih file Excel, lalu mulai scraping.\n")
        self._log("[INFO] F11 = true fullscreen, ESC = keluar dari true fullscreen.\n")
    def _on_closing(self):
        sys.stdout = self._old_stdout
        self.destroy()
    def _open_maximized(self):
        """Membuka window sebesar layar tanpa menghilangkan title bar OS."""
        try:
            self.state("zoomed")
        except Exception:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            self.geometry(f"{screen_w}x{screen_h}+0+0")
    def _toggle_true_fullscreen(self, event=None):
        self._true_fullscreen = not self._true_fullscreen
        self.attributes("-fullscreen", self._true_fullscreen)
    def _exit_true_fullscreen(self, event=None):
        if self._true_fullscreen:
            self._true_fullscreen = False
            self.attributes("-fullscreen", False)
            self.after(50, self._open_maximized)
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._create_sidebar()
        self._create_main_area()
    def _create_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#0D111C")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(18, 8))
        ctk.CTkLabel(
            brand,
            text="Alumni Scrapper",
            font=ctk.CTkFont(size=25, weight="bold"),
            text_color="#EAF2FF"
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand,
            text="Dashboard",
            font=ctk.CTkFont(size=12),
            text_color="#7E8AA6"
        ).pack(anchor="w", pady=(2, 0))
        self._section_label(sidebar, "File Excel Alumni")
        file_card = self._card(sidebar)
        file_card.pack(fill="x", padx=18, pady=(0, 8))
        file_row = ctk.CTkFrame(file_card, fg_color="transparent")
        file_row.pack(fill="x", padx=10, pady=10)
        file_row.grid_columnconfigure(0, weight=1)
        self.file_entry = ctk.CTkEntry(
            file_row,
            textvariable=self.excel_path,
            placeholder_text="Pilih file Excel...",
            height=34,
            border_width=1,
            fg_color="#111827",
            border_color="#26324A",
            text_color="#E5E7EB"
        )
        self.file_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            file_row,
            text="Browse",
            width=78,
            height=34,
            corner_radius=9,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            command=self._browse
        ).grid(row=0, column=1)
        self._section_label(sidebar, "API Keys Apify")
        key_card = self._card(sidebar)
        key_card.pack(fill="x", padx=18, pady=(0, 8))
        self.key_lbl = ctk.CTkLabel(
            key_card,
            text="Belum ada key",
            text_color="#F59E0B",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.key_lbl.pack(anchor="w", padx=10, pady=(9, 4))
        key_add_frame = ctk.CTkFrame(key_card, fg_color="transparent")
        key_add_frame.pack(fill="x", padx=10, pady=(0, 7))
        key_add_frame.grid_columnconfigure(0, weight=1)
        self.key_input = ctk.CTkEntry(
            key_add_frame,
            placeholder_text="apify_api_...",
            height=34,
            border_width=1,
            fg_color="#111827",
            border_color="#26324A",
            text_color="#E5E7EB",
            font=ctk.CTkFont(size=11)
        )
        self.key_input.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.key_input.bind("<Return>", lambda e: self._add_key())
        ctk.CTkButton(
            key_add_frame,
            text="Tambah",
            width=78,
            height=34,
            corner_radius=9,
            fg_color="#16A34A",
            hover_color="#15803D",
            command=self._add_key
        ).grid(row=0, column=1)
        self.key_list_frame = ctk.CTkFrame(
            key_card,
            fg_color="#0B1020",
            corner_radius=10,
            height=76
        )
        self.key_list_frame.pack(fill="x", padx=10, pady=(0, 9))
        self.key_list_frame.pack_propagate(False)
        self._render_key_list()
        self._section_label(sidebar, "Mode Pencarian")
        mode_card = self._card(sidebar)
        mode_card.pack(fill="x", padx=18, pady=(0, 8))
        self.tabs = ctk.CTkTabview(
            mode_card,
            height=214,
            corner_radius=12,
            fg_color="#0B1020",
            segmented_button_fg_color="#111827",
            segmented_button_selected_color="#2563EB",
            segmented_button_selected_hover_color="#1D4ED8"
        )
        self.tabs.pack(fill="x", padx=10, pady=9)
        self._tab_excel(self.tabs.add("Excel"))
        self._tab_manual(self.tabs.add("Manual"))
        action_card = self._card(sidebar)
        action_card.pack(fill="x", padx=18, pady=(0, 12))
        self.start_btn = ctk.CTkButton(
            action_card,
            text="Mulai Scraping",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            corner_radius=11,
            fg_color="#16A34A",
            hover_color="#15803D",
            command=self._start
        )
        self.start_btn.pack(fill="x", padx=10, pady=(10, 7))
        
        control_row = ctk.CTkFrame(action_card, fg_color="transparent")
        control_row.pack(fill="x", padx=10, pady=(0, 10))

        self.pause_btn = ctk.CTkButton(
            control_row,
            text="Pause",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36,
            corner_radius=11,
            fg_color="#D97706",
            hover_color="#B45309",
            state="disabled",
            command=self._toggle_pause
        )
        self.pause_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.stop_btn = ctk.CTkButton(
            control_row,
            text="Stop",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36,
            corner_radius=11,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            state="disabled",
            command=self._stop
        )
        self.stop_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))
    def _section_label(self, parent, text):
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#CBD5E1"
        ).pack(anchor="w", padx=22, pady=(8, 5))
    def _card(self, parent):
        return ctk.CTkFrame(
            parent,
            fg_color="#111827",
            border_width=1,
            border_color="#1F2A44",
            corner_radius=14
        )
    def _tab_excel(self, tab):
        tab.configure(fg_color="#0B1020")
        pad = 5
        ctk.CTkLabel(tab, text="Mulai dari baris", text_color="#B6C2D9", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(7, 2), padx=8)
        self.start_row = ctk.CTkEntry(
            tab,
            placeholder_text="1",
            height=31,
            fg_color="#111827",
            border_color="#26324A",
            text_color="#E5E7EB"
        )
        self.start_row.pack(fill="x", padx=8, pady=(0, pad))
        ctk.CTkLabel(tab, text="Jumlah data", text_color="#B6C2D9", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(0, 2), padx=8)
        self.count_ent = ctk.CTkEntry(
            tab,
            placeholder_text="50",
            height=31,
            fg_color="#111827",
            border_color="#26324A",
            text_color="#E5E7EB"
        )
        self.count_ent.pack(fill="x", padx=8, pady=(0, pad))
        ctk.CTkLabel(tab, text="Output CSV", text_color="#B6C2D9", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(0, 2), padx=8)
        self.out_ent = ctk.CTkEntry(
            tab,
            placeholder_text="auto: data_1_50.csv",
            height=31,
            fg_color="#111827",
            border_color="#26324A",
            text_color="#E5E7EB"
        )
        self.out_ent.pack(fill="x", padx=8)
    def _tab_manual(self, tab):
        tab.configure(fg_color="#0B1020")
        pad = 5
        ctk.CTkLabel(tab, text="Nama alumni", text_color="#B6C2D9", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(7, 2), padx=8)
        self.manual_name = ctk.CTkEntry(
            tab,
            placeholder_text="Budi Santoso",
            height=31,
            fg_color="#111827",
            border_color="#26324A",
            text_color="#E5E7EB"
        )
        self.manual_name.pack(fill="x", padx=8, pady=(0, pad))
        ctk.CTkLabel(tab, text="Output CSV", text_color="#B6C2D9", font=ctk.CTkFont(size=11)).pack(anchor="w", pady=(0, 2), padx=8)
        self.manual_out = ctk.CTkEntry(
            tab,
            placeholder_text="hasil_manual.csv",
            height=31,
            fg_color="#111827",
            border_color="#26324A",
            text_color="#E5E7EB"
        )
        self.manual_out.pack(fill="x", padx=8, pady=(0, pad))
        self.filter_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            tab,
            text="Filter Alumni saja",
            variable=self.filter_var,
            font=ctk.CTkFont(size=11),
            fg_color="#2563EB",
            hover_color="#1D4ED8"
        ).pack(anchor="w", padx=8, pady=(0, pad))
    def _create_main_area(self):
        main = ctk.CTkFrame(self, corner_radius=0, fg_color="#090B12")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=26, pady=(22, 12))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Dashboard Alumni Scrapper",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color="#F8FAFC"
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="Kelola file Excel, API key, progress scraping, dan log proses dalam satu halaman.",
            font=ctk.CTkFont(size=13),
            text_color="#8EA0BE"
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))
        ctk.CTkButton(
            header,
            text="Tutup App",
            width=96,
            height=38,
            corner_radius=10,
            fg_color="#1F2937",
            hover_color="#374151",
            command=self.destroy
        ).grid(row=0, column=1, rowspan=2, sticky="e")
        self._create_stats_cards(main)
        self._create_progress_area(main)
        self._create_log_area(main)
    def _create_stats_cards(self, parent):
        cards_frame = ctk.CTkFrame(parent, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="ew", padx=26, pady=(0, 14))
        cards_data = [
            ("Diproses", "lbl_proc", "0", "#60A5FA"),
            ("Disimpan", "lbl_saved", "0", "#34D399"),
            ("Dilewati", "lbl_skip", "0", "#FBBF24"),
            ("Key Aktif", "lbl_key_no", "-", "#C084FC"),
        ]
        for i, (title, attr, default, color) in enumerate(cards_data):
            cards_frame.grid_columnconfigure(i, weight=1)
            card = ctk.CTkFrame(
                cards_frame,
                fg_color="#111827",
                border_width=1,
                border_color="#1F2A44",
                corner_radius=18
            )
            card.grid(row=0, column=i, padx=(0 if i == 0 else 10, 0), sticky="ew")
            lbl_value = ctk.CTkLabel(
                card,
                text=default,
                font=ctk.CTkFont(size=30, weight="bold"),
                text_color=color
            )
            lbl_value.pack(anchor="w", padx=18, pady=(14, 0))
            ctk.CTkLabel(
                card,
                text=title,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#94A3B8"
            ).pack(anchor="w", padx=18, pady=(0, 14))
            setattr(self, attr, lbl_value)
    def _create_progress_area(self, parent):
        prog_frame = ctk.CTkFrame(
            parent,
            fg_color="#111827",
            border_width=1,
            border_color="#1F2A44",
            corner_radius=18
        )
        prog_frame.grid(row=2, column=0, sticky="ew", padx=26, pady=(0, 14))
        prog_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            prog_frame,
            text="Progress Proses",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#E5E7EB"
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 6))
        self.prog_bar = ctk.CTkProgressBar(
            prog_frame,
            height=18,
            corner_radius=9,
            progress_color="#2563EB",
            fg_color="#0B1020"
        )
        self.prog_bar.set(0)
        self.prog_bar.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))
        self.prog_lbl = ctk.CTkLabel(
            prog_frame,
            text="Siap.",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        self.prog_lbl.grid(row=2, column=0, sticky="w", padx=18, pady=(0, 14))
    def _create_log_area(self, parent):
        log_panel = ctk.CTkFrame(
            parent,
            fg_color="#111827",
            border_width=1,
            border_color="#1F2A44",
            corner_radius=18
        )
        log_panel.grid(row=3, column=0, sticky="nsew", padx=26, pady=(0, 22))
        log_panel.grid_columnconfigure(0, weight=1)
        log_panel.grid_rowconfigure(1, weight=1)
        log_header = ctk.CTkFrame(log_panel, fg_color="transparent")
        log_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 9))
        log_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            log_header,
            text="Log Output",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#E5E7EB"
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            log_header,
            text="Clear",
            width=84,
            height=32,
            corner_radius=10,
            fg_color="#1F2937",
            hover_color="#374151",
            command=self._clear_log
        ).grid(row=0, column=1, sticky="e")
        self.log_box = ctk.CTkTextbox(
            log_panel,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#050816",
            text_color="#E5E7EB",
            corner_radius=14,
            border_width=1,
            border_color="#1F2A44"
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.log_box.configure(state="disabled")
    def _poll_log(self):
        try:
            while True:
                text = self.log_q.get_nowait()
                self.log_box.configure(state="normal")
                self.log_box.insert("end", text)
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(80, self._poll_log)
    def _log(self, msg):
        self.log_q.put(msg)
    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
    # ------------------------------------------------------------------
    # API KEY MANAGEMENT
    # ------------------------------------------------------------------
    def _load_keys(self):
        try:
            if os.path.exists("api_keys.json"):
                with open("api_keys.json", "r", encoding="utf-8") as f:
                    self._api_keys = json.load(f)
                    if not isinstance(self._api_keys, list):
                        self._api_keys = []
        except Exception as e:
            self._log(f"[ERROR] Gagal memuat API keys: {e}\n")

    def _save_keys(self):
        try:
            with open("api_keys.json", "w", encoding="utf-8") as f:
                json.dump(self._api_keys, f, indent=4)
        except Exception as e:
            self._log(f"[ERROR] Gagal menyimpan API keys: {e}\n")

    def _add_key(self):
        key = self.key_input.get().strip()
        if not key:
            return
        if key in self._api_keys:
            messagebox.showwarning("Duplikat", "Key ini sudah ada dalam daftar.")
            return
        self._api_keys.append(key)
        self._save_keys()
        self.key_input.delete(0, "end")
        self._render_key_list()
        self._rebuild_key_mgr()
        self._log(f"[+] API Key #{len(self._api_keys)} ditambahkan.\n")
    def _remove_key(self, idx):
        if 0 <= idx < len(self._api_keys):
            removed = self._api_keys.pop(idx)
            self._save_keys()
            self._render_key_list()
            self._rebuild_key_mgr()
            self._log(f"[-] Key #{idx + 1} dihapus (...{removed[-8:]})\n")
    def _render_key_list(self):
        for w in self.key_list_frame.winfo_children():
            w.destroy()
        self._key_rows.clear()
        if not self._api_keys:
            ctk.CTkLabel(
                self.key_list_frame,
                text="Belum ada key ditambahkan.",
                text_color="#6B7280",
                font=ctk.CTkFont(size=10)
            ).pack(pady=10)
            return
        max_show = 2
        start_index = max(0, len(self._api_keys) - max_show)
        shown_keys = self._api_keys[start_index:]
        for offset, k in enumerate(shown_keys):
            real_index = start_index + offset
            row = ctk.CTkFrame(self.key_list_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=3)
            row.grid_columnconfigure(0, weight=1)
            masked = f"#{real_index + 1}  ...{k[-10:]}"
            ctk.CTkLabel(
                row,
                text=masked,
                font=ctk.CTkFont(family="Consolas", size=10),
                text_color="#CBD5E1"
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkButton(
                row,
                text="X",
                width=26,
                height=22,
                corner_radius=7,
                fg_color="#7F1D1D",
                hover_color="#991B1B",
                font=ctk.CTkFont(size=10, weight="bold"),
                command=lambda idx=real_index: self._remove_key(idx)
            ).grid(row=0, column=1, padx=(6, 0))
            self._key_rows.append(row)
        if len(self._api_keys) > max_show:
            ctk.CTkLabel(
                self.key_list_frame,
                text=f"+ {len(self._api_keys) - max_show} key lainnya",
                text_color="#7E8AA6",
                font=ctk.CTkFont(size=10)
            ).pack(anchor="w", padx=8, pady=(0, 2))
    def _rebuild_key_mgr(self):
        if self._api_keys:
            self.key_mgr = ApiKeyManager(self._api_keys)
            self.key_lbl.configure(
                text=f"{len(self._api_keys)} key aktif • auto-rotate",
                text_color="#34D399"
            )
            self.lbl_key_no.configure(text=f"#{self.key_mgr.current_index + 1}")
        else:
            self.key_mgr = None
            self.key_lbl.configure(text="Belum ada key", text_color="#F59E0B")
            self.lbl_key_no.configure(text="-")
    def _browse(self):
        path = filedialog.askopenfilename(
            title="Pilih File Excel Alumni",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("All Files", "*.*")]
        )
        if path:
            self.excel_path.set(path)
            self._log(f"[FILE] {os.path.basename(path)}\n")
    def _validate_ready(self):
        if not self.key_mgr:
            messagebox.showerror("API Key", "Belum ada API key! Tambah dulu di panel kiri.")
            return False
        return True
    def _set_running(self, running: bool):
        self.is_running = running
        self.start_btn.configure(state="disabled" if running else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")
        self.pause_btn.configure(state="normal" if running else "disabled", text="Pause")
        self.pause_event.clear()

    def _toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_btn.configure(text="Pause")
            self._log("\n[INFO] Melanjutkan proses scraping...\n")
        else:
            self.pause_event.set()
            self.pause_btn.configure(text="Resume")
            self._log("\n[INFO] Proses scraping dijeda sementara (Pause)...\n")

    def _update_stats(self):
        self.lbl_proc.configure(text=str(self._processed))
        self.lbl_saved.configure(text=str(self._saved))
        self.lbl_skip.configure(text=str(self._skipped))
        if self.key_mgr:
            self.lbl_key_no.configure(text=f"#{self.key_mgr.current_index + 1}")
        else:
            self.lbl_key_no.configure(text="-")
        if self._total > 0:
            progress = min(self._processed / self._total, 1)
            self.prog_bar.set(progress)
            self.prog_lbl.configure(
                text=(
                    f"Progress: {self._processed}/{self._total}  •  "
                    f"Disimpan: {self._saved}  •  Dilewati: {self._skipped}"
                )
            )
    def _start(self):
        tab = self.tabs.get()
        if "Excel" in tab:
            self._start_excel()
        else:
            self._search_manual()
    def _start_excel(self):
        if not self._validate_ready():
            return
        path = self.excel_path.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showerror("File", "Pilih file Excel yang valid terlebih dahulu!")
            return
        try:
            mulai = int(self.start_row.get().strip() or "1")
            jumlah = int(self.count_ent.get().strip() or "50")
        except ValueError:
            messagebox.showerror("Input", "Mulai baris dan jumlah data harus angka!")
            return
        if mulai < 1 or jumlah < 1:
            messagebox.showerror("Input", "Mulai baris dan jumlah data minimal 1.")
            return
        out = self.out_ent.get().strip()
        baris_akhir = mulai + jumlah - 1
        file_out = out if out else f"data_{mulai}_{baris_akhir}.csv"
        if not file_out.endswith(".csv"):
            file_out += ".csv"
        self._processed = 0
        self._saved = 0
        self._skipped = 0
        self._total = jumlah
        self.prog_bar.set(0)
        self.prog_lbl.configure(text="Menyiapkan proses scraping...")
        self._update_stats()
        self.stop_event.clear()
        self._set_running(True)
        self._log(
            f"\n{'=' * 55}\n"
            f"MULAI SCRAPING EXCEL\n"
            f"Baris {mulai} s/d {baris_akhir} | Output: {file_out}\n"
            f"{'=' * 55}\n"
        )
        t = threading.Thread(
            target=self._run_excel,
            args=(path, mulai, jumlah, baris_akhir, file_out),
            daemon=True
        )
        t.start()
    def _run_excel(self, path, mulai, jumlah, baris_akhir, file_out):
        try:
            df = pd.read_excel(path)
        except Exception as e:
            self._log(f"[ERROR] Gagal baca Excel: {e}\n")
            self.after(0, lambda: self._set_running(False))
            return
        index_awal = mulai - 1
        df_sub = df.iloc[index_awal: index_awal + jumlah]
        if df_sub.empty:
            self._log("[ERROR] Tidak ada data pada rentang baris tersebut.\n")
            self.after(0, lambda: self._set_running(False))
            return
        self._total = len(df_sub)
        self.after(0, self._update_stats)
        for step, (index, row) in enumerate(df_sub.iterrows(), start=1):
            if self.stop_event.is_set():
                self._log("\n[STOP] Scraping dihentikan oleh user.\n")
                break
                
            while self.pause_event.is_set() and not self.stop_event.is_set():
                time.sleep(0.5)
                
            if self.stop_event.is_set():
                break
                
            nama = row.get("Nama Lulusan", "")
            nim = row.get("NIM", "Tidak dicantumkan")
            tmasuk = row.get("Tahun Masuk", "Tidak dicantumkan")
            tlulus = row.get("Tanggal Lulus", "Tidak dicantumkan")
            fak = row.get("Fakultas", "Tidak dicantumkan")
            prodi = row.get("Program Studi", "Tidak dicantumkan")
            first, last = pisahkan_nama(nama)
            print(f"\n{'-' * 50}")
            print(f"[{step}/{len(df_sub)}] {self.key_mgr.status()}")
            print(f"Baris: {index + 1} | Nama: {first} {last}")
            self._processed += 1
            if not first and not last:
                print("[SKIP] Baris kosong, dilewati.")
                self._skipped += 1
                self.after(0, self._update_stats)
                continue
            cp = {
                "mulai_baris": mulai,
                "baris_akhir": baris_akhir,
                "file_output": file_out,
                "last_excel_index": index - 1,
                "current_key_index": self.key_mgr.current_index,
            }
            ok, items = panggil_apify(self.key_mgr, first, last, checkpoint_data=cp)
            if ok is None:
                self._log("\n[STOP] Program dihentikan karena API key habis.\n")
                break
            if ok and items:
                simpan = proses_hasil(
                    items,
                    nama,
                    nim,
                    tmasuk,
                    tlulus,
                    fak,
                    prodi,
                    file_out,
                    filter_umm=True
                )
                if simpan:
                    print("   [OK] DISIMPAN: Alumni UMM terdeteksi.")
                    self._saved += 1
                else:
                    print("   [--] Bukan Alumni UMM.")
                    self._skipped += 1
            else:
                print("   [--] Profil tidak ditemukan.")
                self._skipped += 1
            self.after(0, self._update_stats)
        print(f"\n{'=' * 50}")
        print(f"SELESAI! Disimpan: {self._saved} | Dilewati: {self._skipped}")
        print(f"Output: {file_out}")
        self.after(0, self._finish_excel_ui(file_out))
    def _finish_excel_ui(self, file_out):
        def done():
            self._set_running(False)
            if self._total > 0:
                self.prog_bar.set(min(self._processed / self._total, 1))
            self.prog_lbl.configure(text=f"Selesai • {self._saved} data tersimpan di {file_out}")
        return done
    def _stop(self):
        self.stop_event.set()
        self._log("\n[STOP] Menghentikan setelah baris ini selesai...\n")
    def _search_manual(self):
        if not self._validate_ready():
            return
        nama = self.manual_name.get().strip()
        if not nama:
            messagebox.showerror("Input", "Masukkan nama alumni terlebih dahulu!")
            return
        out = self.manual_out.get().strip() or "hasil_manual.csv"
        if not out.endswith(".csv"):
            out += ".csv"
        filter_umm = self.filter_var.get()
        
        self._set_running(True)
        self.prog_bar.set(0)
        self.prog_lbl.configure(text=f"Mencari data untuk: {nama}...")
        
        self._log(f"\n[CARI] {nama} | Output: {out}\n")
        t = threading.Thread(target=self._run_manual, args=(nama, out, filter_umm), daemon=True)
        t.start()
    def _run_manual(self, nama, out, filter_umm):
        first, last = pisahkan_nama(nama)
        if not first:
            self._log("[ERROR] Nama tidak valid.\n")
            return
        print(f"Mencari: {first} {last} | {self.key_mgr.status()}")
        ok, items = panggil_apify(self.key_mgr, first, last)
        if ok and items:
            simpan = proses_hasil(
                items,
                nama,
                "Tidak dicantumkan",
                "Tidak dicantumkan",
                "Tidak dicantumkan",
                "Tidak dicantumkan",
                "Tidak dicantumkan",
                out,
                filter_umm=filter_umm
            )
            if simpan:
                label = "Alumni UMM ditemukan" if filter_umm else "Profil ditemukan"
                print(f"[OK] {label} -> tersimpan di {out}")
            else:
                label = "Bukan Alumni UMM" if filter_umm else "Tidak ada profil cocok"
                print(f"[--] {label}.")
        elif ok is None:
            print("[STOP] API key habis.")
        else:
            print("[--] Profil tidak ditemukan di LinkedIn.")
            
        print(f"\n{'=' * 50}")
        print(f"Pencarian manual selesai. Output tersimpan di: {out}")
        self.after(0, self._finish_manual_ui(out))

    def _finish_manual_ui(self, out):
        def done():
            self._set_running(False)
            self.prog_bar.set(1)
            self.prog_lbl.configure(text=f"Selesai • Hasil manual disimpan di {out}")
        return done
if __name__ == "__main__":
    app = ScraperApp()
    app.mainloop()
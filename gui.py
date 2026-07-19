#!/usr/bin/env python3
"""
Jy Music — GUI
Music library manager + player + converter — all in one.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).parent))

from database import MusicDB
from player import get_player
from scanner import (SUBPROCESS_FLAGS, SUPPORTED_EXTS, find_ffmpeg,
                     probe_file, quick_scan)
from version import APP_NAME, DONATE_URL, REPO_URL, __version__

try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def user_data_dir():
    if not getattr(sys, "frozen", False):
        return Path(__file__).parent
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get(
            "XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    d = base / "JyMusic"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_settings():
    try:
        with open(user_data_dir() / "settings.json", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(**kw):
    s = load_settings()
    s.update(kw)
    try:
        with open(user_data_dir() / "settings.json", "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


# ═══════════════════════════════════════════════════════════════
# Fonts (cross-platform)
# ═══════════════════════════════════════════════════════════════

def _resolve_font():
    if sys.platform == "win32":
        return "Microsoft YaHei UI"
    elif sys.platform == "darwin":
        return "PingFang SC"
    return "Noto Sans CJK SC"

_UI_FONT = _resolve_font()

F = {
    "h1":   (_UI_FONT, 15, "bold"),
    "h2":   (_UI_FONT, 11),
    "body": (_UI_FONT, 10),
    "sm":   (_UI_FONT, 9),
    "ctrl": (_UI_FONT, 16),
}


# ═══════════════════════════════════════════════════════════════
# Themes — minimalist
# ═══════════════════════════════════════════════════════════════

THEMES = {
    "light": {
        "bg":       "#ffffff",
        "surface":  "#f7f7f7",
        "card":     "#ffffff",
        "border":   "#ebebeb",
        "text":     "#1a1a1a",
        "dim":      "#999999",
        "accent":   "#0066ff",
        "accent2":  "#0052cc",
        "green":    "#22c55e",
        "red":      "#ef4444",
        "yellow":   "#eab308",
        "progress": "#0066ff",
    },
    "dark": {
        "bg":       "#111111",
        "surface":  "#1a1a1a",
        "card":     "#222222",
        "border":   "#2e2e2e",
        "text":     "#eeeeee",
        "dim":      "#666666",
        "accent":   "#4d9fff",
        "accent2":  "#3d8bff",
        "green":    "#4ade80",
        "red":      "#f87171",
        "yellow":   "#fbbf24",
        "progress": "#4d9fff",
    },
    "anime": {
        "bg":       "#fff5f8",
        "surface":  "#fff0f3",
        "card":     "#ffffff",
        "border":   "#ffd6e0",
        "text":     "#3d1a2e",
        "dim":      "#c48fa3",
        "accent":   "#ff4d8d",
        "accent2":  "#c084fc",
        "green":    "#86dba6",
        "red":      "#ff6b6b",
        "yellow":   "#f5c842",
        "progress": "#ff4d8d",
    },
}


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _hover(widget, normal_bg, hover_bg):
    widget.bind("<Enter>", lambda e: widget.configure(bg=hover_bg))
    widget.bind("<Leave>", lambda e: widget.configure(bg=normal_bg))


def _blend(hex_color, factor=0.92):
    """Darken (factor<1) or lighten a hex color toward white (factor>1)."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    if factor < 1:
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
    else:
        r = min(255, r + int((255 - r) * (factor - 1)))
        g = min(255, g + int((255 - g) * (factor - 1)))
        b = min(255, b + int((255 - b) * (factor - 1)))
    return f"#{r:02x}{g:02x}{b:02x}"


# ═══════════════════════════════════════════════════════════════
# App
# ═══════════════════════════════════════════════════════════════

class JyMusic:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1060x660")
        self.root.minsize(820, 520)

        self.db = MusicDB(str(user_data_dir() / "music.db"))
        self.player = get_player()

        saved_theme = load_settings().get("theme", "light")
        self.theme = THEMES.get(saved_theme, THEMES["light"])
        self._theme_name = saved_theme if saved_theme in THEMES else "light"

        self.current_playlist = None
        self.play_queue = []
        self.queue_index = -1
        self._current_art = None

        self.root.configure(bg=self.theme["bg"])
        self._build_ui()
        self._refresh_library()
        self._refresh_playlists()
        self._update_player_ui()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # Easter egg: Ctrl+Shift+A toggles anime theme
        self.root.bind("<Control-Shift-A>", lambda e: self._set_theme("anime"))
        self.root.bind("<Control-Shift-a>", lambda e: self._set_theme("anime"))

    def _on_close(self):
        self.player.stop()
        self.db.close()
        self.root.destroy()

    # ═══════════════════════════════════════════════════════════
    # UI Build
    # ═══════════════════════════════════════════════════════════

    def _build_ui(self):
        T = self.theme

        # ── Top bar ──
        self.topbar = tk.Frame(self.root, bg=T["bg"], height=48)
        self.topbar.pack(fill="x", side="top")
        self.topbar.pack_propagate(False)

        self.app_title = tk.Label(
            self.topbar, text=APP_NAME, fg=T["text"], bg=T["bg"],
            font=F["h1"])
        self.app_title.pack(side="left", padx=(20, 0), pady=10)

        # Right side of topbar: theme toggle + menu
        self.menu_btn = tk.Label(
            self.topbar, text="···", fg=T["dim"], bg=T["bg"],
            font=(_UI_FONT, 16), cursor="hand2")
        self.menu_btn.pack(side="right", padx=(0, 16))
        self.menu_btn.bind("<Button-1>", self._show_menu)
        _hover(self.menu_btn, T["bg"], T["surface"])

        self.theme_btn = tk.Label(
            self.topbar, text="◐", fg=T["dim"], bg=T["bg"],
            font=(_UI_FONT, 14), cursor="hand2")
        self.theme_btn.pack(side="right", padx=(0, 12))
        self.theme_btn.bind("<Button-1>", lambda e: self._toggle_theme())
        _hover(self.theme_btn, T["bg"], T["surface"])

        # Search in topbar
        self.search_frame = tk.Frame(self.topbar, bg=T["bg"])
        self.search_frame.pack(side="right", padx=(0, 16), pady=12)

        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self._on_search())
        self.search_entry = tk.Entry(
            self.search_frame, textvariable=self.search_var, width=24,
            bg=T["surface"], fg=T["text"], insertbackground=T["text"],
            font=F["body"], borderwidth=0, relief="flat")
        self.search_entry.pack(ipady=4, padx=8)
        self.search_entry.insert(0, "")
        self.search_entry.bind("<FocusIn>", self._search_focus_in)
        self.search_entry.bind("<FocusOut>", self._search_focus_out)

        # Separator
        self.top_sep = tk.Frame(self.root, bg=T["border"], height=1)
        self.top_sep.pack(fill="x", side="top")

        # ── Player bar (bottom) ──
        self.player_frame = tk.Frame(self.root, bg=T["surface"], height=64)
        self.player_frame.pack(fill="x", side="bottom")
        self.player_frame.pack_propagate(False)

        self.bottom_sep = tk.Frame(self.root, bg=T["border"], height=1)
        self.bottom_sep.pack(fill="x", side="bottom")

        # Album art
        self.art_label = tk.Label(
            self.player_frame, bg=T["border"], width=6, height=3)
        self.art_label.pack(side="left", padx=(12, 8), pady=8)

        # Song info
        info_frame = tk.Frame(self.player_frame, bg=T["surface"])
        info_frame.pack(side="left", padx=(0, 16))

        self.np_title = tk.Label(
            info_frame, text="未播放", fg=T["text"], bg=T["surface"],
            font=F["body"], anchor="w")
        self.np_title.pack(anchor="w")
        self.np_artist = tk.Label(
            info_frame, text="", fg=T["dim"], bg=T["surface"],
            font=F["sm"], anchor="w")
        self.np_artist.pack(anchor="w")

        # Controls (center)
        ctrl_frame = tk.Frame(self.player_frame, bg=T["surface"])
        ctrl_frame.pack(side="left", expand=True)

        btn_cfg = {"bg": T["surface"], "fg": T["text"],
                   "font": F["ctrl"], "borderwidth": 0,
                   "cursor": "hand2", "activebackground": T["surface"],
                   "activeforeground": T["accent"]}

        self.btn_prev = tk.Button(ctrl_frame, text="⏮", command=self._prev, **btn_cfg)
        self.btn_prev.pack(side="left", padx=4)
        _hover(self.btn_prev, T["surface"], T["surface"])

        self.btn_play = tk.Button(ctrl_frame, text="▶", command=self._play_pause, **btn_cfg)
        self.btn_play.pack(side="left", padx=4)
        _hover(self.btn_play, T["surface"], T["surface"])

        self.btn_next = tk.Button(ctrl_frame, text="⏭", command=self._next, **btn_cfg)
        self.btn_next.pack(side="left", padx=4)
        _hover(self.btn_next, T["surface"], T["surface"])

        # Seek bar
        seek_frame = tk.Frame(self.player_frame, bg=T["surface"])
        seek_frame.pack(side="left", expand=True, fill="x", padx=8)

        self.seek_var = tk.DoubleVar()
        self.seek_scale = tk.Scale(
            seek_frame, from_=0, to=1000, orient="horizontal",
            variable=self.seek_var, command=self._on_seek,
            bg=T["surface"], fg=T["progress"], troughcolor=T["border"],
            highlightthickness=0, borderwidth=0, showvalue=0,
            sliderrelief="flat",
        )
        self.seek_scale.pack(fill="x", expand=True)

        # Time + Volume
        right_frame = tk.Frame(self.player_frame, bg=T["surface"])
        right_frame.pack(side="right", padx=(0, 16))

        self.time_label = tk.Label(
            right_frame, text="0:00", fg=T["dim"], bg=T["surface"],
            font=F["sm"])
        self.time_label.pack(side="left", padx=(0, 12))

        self.vol_scale = tk.Scale(
            right_frame, from_=0, to=100, orient="horizontal",
            command=self._on_volume, length=80, showvalue=0,
            bg=T["surface"], troughcolor=T["border"],
            highlightthickness=0, borderwidth=0, sliderrelief="flat",
        )
        self.vol_scale.set(100)
        self.vol_scale.pack(side="left")

        # ── Main content ──
        self.main = tk.Frame(self.root, bg=T["bg"])
        self.main.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = tk.Frame(self.main, bg=T["bg"], width=180)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Sidebar: Library section
        tk.Label(self.sidebar, text="资料库", fg=T["dim"], bg=T["bg"],
                 font=F["sm"]).pack(anchor="w", padx=16, pady=(16, 4))

        self._lib_all_btn = tk.Label(
            self.sidebar, text="全部歌曲", fg=T["text"], bg=T["bg"],
            font=F["body"], cursor="hand2", anchor="w")
        self._lib_all_btn.pack(fill="x", padx=16, pady=2)
        self._lib_all_btn.bind("<Button-1>", lambda e: self._show_all())
        _hover(self._lib_all_btn, T["bg"], T["surface"])

        self._lib_recent_btn = tk.Label(
            self.sidebar, text="最近添加", fg=T["text"], bg=T["bg"],
            font=F["body"], cursor="hand2", anchor="w")
        self._lib_recent_btn.pack(fill="x", padx=16, pady=2)
        self._lib_recent_btn.bind("<Button-1>", lambda e: self._show_recent())
        _hover(self._lib_recent_btn, T["bg"], T["surface"])

        # Sidebar: separator
        sep = tk.Frame(self.sidebar, bg=T["border"], height=1)
        sep.pack(fill="x", padx=16, pady=10)

        # Sidebar: Playlists section
        pl_header = tk.Frame(self.sidebar, bg=T["bg"])
        pl_header.pack(fill="x", padx=16)
        tk.Label(pl_header, text="播放列表", fg=T["dim"], bg=T["bg"],
                 font=F["sm"]).pack(side="left")
        self._pl_add_btn = tk.Label(
            pl_header, text="+", fg=T["dim"], bg=T["bg"],
            font=(_UI_FONT, 14), cursor="hand2")
        self._pl_add_btn.pack(side="right")
        self._pl_add_btn.bind("<Button-1>", lambda e: self._new_playlist_dialog())
        _hover(self._pl_add_btn, T["bg"], T["surface"])

        pl_container = tk.Frame(self.sidebar, bg=T["bg"])
        pl_container.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        self.pl_listbox = tk.Listbox(
            pl_container, bg=T["bg"], fg=T["text"],
            font=F["body"], selectbackground=T["surface"],
            selectforeground=T["text"], borderwidth=0,
            highlightthickness=0, activestyle="none",
        )
        pl_scroll = tk.Scrollbar(pl_container, orient="vertical",
                                 command=self.pl_listbox.yview)
        self.pl_listbox.configure(yscrollcommand=pl_scroll.set)
        pl_scroll.pack(side="right", fill="y")
        self.pl_listbox.pack(side="left", fill="both", expand=True)
        self.pl_listbox.bind("<<ListboxSelect>>", self._on_playlist_select)
        self.pl_listbox.bind("<Double-Button-1>", self._play_playlist)

        # Vertical separator between sidebar and content
        self.side_sep = tk.Frame(self.main, bg=T["border"], width=1)
        self.side_sep.pack(side="left", fill="y")

        # Right content area
        content = tk.Frame(self.main, bg=T["bg"])
        content.pack(side="left", fill="both", expand=True)

        # Song count
        self.count_label = tk.Label(
            content, text="", fg=T["dim"], bg=T["bg"],
            font=F["sm"], anchor="w")
        self.count_label.pack(fill="x", padx=16, pady=(12, 4))

        # Song list (Treeview)
        tree_frame = tk.Frame(content, bg=T["bg"])
        tree_frame.pack(fill="both", expand=True, padx=(16, 0))

        columns = ("title", "artist", "album", "duration", "format")
        self.tree = ttk.Treeview(tree_frame, columns=columns,
                                 show="headings", selectmode="extended")
        self.tree.heading("title", text="标题")
        self.tree.heading("artist", text="艺术家")
        self.tree.heading("album", text="专辑")
        self.tree.heading("duration", text="时长")
        self.tree.heading("format", text="格式")

        self.tree.column("title", width=260, minwidth=100, stretch=True)
        self.tree.column("artist", width=150, minwidth=60, stretch=True)
        self.tree.column("album", width=150, minwidth=60, stretch=True)
        self.tree.column("duration", width=60, minwidth=50, stretch=False, anchor="center")
        self.tree.column("format", width=50, minwidth=40, stretch=False, anchor="center")

        tree_scroll = tk.Scrollbar(tree_frame, orient="vertical",
                                   command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        # Style treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=T["bg"],
                        foreground=T["text"],
                        fieldbackground=T["bg"],
                        font=F["body"],
                        rowheight=32)
        style.configure("Treeview.Heading",
                        background=T["bg"],
                        foreground=T["dim"],
                        font=F["sm"],
                        borderwidth=0,
                        relief="flat")
        style.map("Treeview",
                  background=[("selected", T["accent"])],
                  foreground=[("selected", "#ffffff")])
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

        # Context menu
        self.tree_menu = tk.Menu(self.root, tearoff=0, bg=T["card"],
                                 fg=T["text"], activebackground=T["accent"],
                                 activeforeground="white", font=F["body"])
        self.tree_menu.add_command(label="播放", command=self._play_selected)
        self.tree_menu.add_command(label="添加到播放列表",
                                   command=self._add_to_playlist_dialog)
        self.tree_menu.add_command(label="编辑标签", command=self._edit_tags)
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="从库中删除", command=self._delete_selected)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Button-2>", self._on_right_click)
        self.tree.bind("<Double-1>", lambda e: self._play_selected())

        # Dropdown menu (three dots)
        self._dropdown = tk.Menu(self.root, tearoff=0, bg=T["card"],
                                 fg=T["text"], activebackground=T["accent"],
                                 activeforeground="white", font=F["body"])
        self._dropdown.add_command(label="扫描文件夹...", command=self._scan_dir)
        self._dropdown.add_command(label="格式转换...", command=self._open_converter)
        self._dropdown.add_separator()
        self._dropdown.add_command(label="支持作者",
                                   command=lambda: webbrowser.open(DONATE_URL or REPO_URL))
        self._dropdown.add_command(label="GitHub",
                                   command=lambda: webbrowser.open(REPO_URL))
        self._dropdown.add_separator()
        self._dropdown.add_command(label="关于", command=self._about_dialog)

        # Timer
        self._update_timer()

    # ═══════════════════════════════════════════════════════════
    # Search
    # ═══════════════════════════════════════════════════════════

    def _search_focus_in(self, event):
        self.search_entry.configure(bg=self.theme["card"])

    def _search_focus_out(self, event):
        self.search_entry.configure(bg=self.theme["surface"])

    def _show_menu(self, event):
        try:
            self._dropdown.tk_popup(event.x_root, event.y_root)
        finally:
            self._dropdown.grab_release()

    def _show_all(self):
        self.current_playlist = None
        self._refresh_library()

    def _show_recent(self):
        self.current_playlist = None
        songs = self.db.get_all_songs(order="date_added DESC")
        self._refresh_library(songs[:50] if len(songs) > 50 else songs)

    # ═══════════════════════════════════════════════════════════
    # Library
    # ═══════════════════════════════════════════════════════════

    def _refresh_library(self, songs=None):
        self.tree.delete(*self.tree.get_children())
        if songs is None:
            songs = self.db.get_all_songs()

        for s in songs:
            dur = s[7]
            dur_str = f"{int(dur//60)}:{int(dur%60):02d}" if dur else "-:--"
            self.tree.insert("", "end", iid=str(s[0]),
                             values=(s[2], s[3], s[4], dur_str, s[8]))

        count = len(songs) if songs else self.db.count_songs()
        self.count_label.config(text=f"{count} 首歌曲")

    def _on_search(self):
        q = self.search_var.get().strip()
        if not q:
            self._refresh_library()
        else:
            rows = self.db.search(q)
            self._refresh_library(rows)

    def _get_selected_ids(self):
        return [int(i) for i in self.tree.selection()]

    # ═══════════════════════════════════════════════════════════
    # Playback
    # ═══════════════════════════════════════════════════════════

    def _play_song_id(self, song_id):
        song = self.db.get_song(song_id)
        if not song:
            return
        file_path = song[1]
        title = song[2] or Path(file_path).stem
        artist = song[3] or ""

        def on_end(event_type):
            if event_type == "ended":
                self.root.after(0, self._next)

        ok = self.player.play(file_path, song_id, on_end)
        if ok:
            self.np_title.config(text=title, fg=self.theme["text"])
            self.np_artist.config(text=artist)
            self._update_player_ui()
            self._load_cover_art(file_path)

    def _load_cover_art(self, file_path):
        if not _HAS_PIL:
            return

        def _extract():
            ffmpeg = find_ffmpeg()
            if not ffmpeg:
                return
            tmp = Path(tempfile.gettempdir()) / "jymusic_cover.png"
            try:
                subprocess.run(
                    [ffmpeg, "-y", "-i", str(file_path), "-an",
                     "-vcodec", "png", "-frames:v", "1", str(tmp)],
                    capture_output=True, timeout=5, **SUBPROCESS_FLAGS)
                if tmp.exists() and tmp.stat().st_size > 0:
                    img = Image.open(tmp).resize((44, 44), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self._current_art = photo
                    self.root.after(0, lambda: self.art_label.configure(
                        image=photo, width=44, height=44))
                    return
            except Exception:
                pass
            self.root.after(0, lambda: self.art_label.configure(
                image="", width=6, height=3))

        threading.Thread(target=_extract, daemon=True).start()

    def _play_selected(self):
        ids = self._get_selected_ids()
        if not ids:
            return
        self.play_queue = ids
        self.queue_index = 0
        self._play_song_id(ids[0])

    def _play_playlist(self, event=None):
        sel = self.pl_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        pl_data = self._playlist_data[idx]
        pid = pl_data[0]
        songs = self.db.get_playlist_songs(pid)
        if not songs:
            messagebox.showinfo("提示", "播放列表为空")
            return
        self.play_queue = [s[0] for s in songs]
        self.queue_index = 0
        self._play_song_id(self.play_queue[0])

    def _play_pause(self):
        if self.player.is_playing:
            if self.player.is_paused:
                self.player.resume()
            else:
                self.player.pause()
        else:
            sel = self._get_selected_ids()
            if sel:
                self._play_selected()
        self._update_player_ui()

    def _next(self):
        if not self.play_queue:
            return
        self.queue_index = (self.queue_index + 1) % len(self.play_queue)
        self._play_song_id(self.play_queue[self.queue_index])

    def _prev(self):
        if not self.play_queue:
            return
        self.queue_index = (self.queue_index - 1) % len(self.play_queue)
        self._play_song_id(self.play_queue[self.queue_index])

    def _on_volume(self, val):
        self.player.set_volume(float(val) / 100)

    def _on_seek(self, val):
        try:
            song = self.player.current
            if song:
                sid = song[0]
                s = self.db.get_song(sid)
                if s:
                    dur = s[7]
                    if dur:
                        self.player.seek(float(val) / 1000 * dur)
        except Exception:
            pass

    def _update_player_ui(self):
        if self.player.is_playing:
            self.btn_play.config(text="⏸" if not self.player.is_paused else "▶")
        else:
            self.btn_play.config(text="▶")

    def _update_timer(self):
        if self.player.is_playing and not self.player.is_paused:
            pos = self.player.get_pos()
            song = self.player.current
            dur = 0
            if song:
                s = self.db.get_song(song[0])
                if s:
                    dur = s[7]
            if dur > 0 and pos < dur:
                self.time_label.config(
                    text=f"{int(pos//60)}:{int(pos%60):02d} / "
                         f"{int(dur//60)}:{int(dur%60):02d}")
                self.seek_var.set(pos / dur * 1000)
        self.root.after(500, self._update_timer)

    # ═══════════════════════════════════════════════════════════
    # Playlists
    # ═══════════════════════════════════════════════════════════

    def _refresh_playlists(self):
        self.pl_listbox.delete(0, "end")
        self._playlist_data = self.db.list_playlists()
        for p in self._playlist_data:
            self.pl_listbox.insert("end", f"  {p[1]}  ({p[3]})")

    def _on_playlist_select(self, event):
        sel = self.pl_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        pl_data = self._playlist_data[idx]
        pid = pl_data[0]
        songs = self.db.get_playlist_songs(pid)
        self._refresh_library(songs)
        self.current_playlist = pid

    def _new_playlist_dialog(self):
        T = self.theme
        dlg = tk.Toplevel(self.root)
        dlg.title("新建播放列表")
        dlg.geometry("320x140")
        dlg.configure(bg=T["bg"])
        dlg.transient(self.root)
        dlg.grab_set()
        self._center_dialog(dlg)

        tk.Label(dlg, text="名称", bg=T["bg"], fg=T["dim"],
                 font=F["sm"]).pack(anchor="w", padx=24, pady=(24, 4))
        var = tk.StringVar()
        entry = tk.Entry(dlg, textvariable=var, width=30, bg=T["surface"],
                         fg=T["text"], font=F["body"],
                         insertbackground=T["text"], borderwidth=0, relief="flat")
        entry.pack(padx=24, ipady=5)
        entry.focus_set()

        btn = tk.Button(dlg, text="创建", bg=T["accent"], fg="white",
                        font=F["body"], padx=20, pady=4, borderwidth=0,
                        cursor="hand2",
                        command=lambda: self._create_playlist(var.get(), dlg))
        btn.pack(pady=16)
        _hover(btn, T["accent"], T["accent2"])
        dlg.bind("<Return>", lambda e: self._create_playlist(var.get(), dlg))

    def _create_playlist(self, name, dlg):
        if name.strip():
            self.db.create_playlist(name.strip())
            self._refresh_playlists()
        dlg.destroy()

    def _delete_playlist(self):
        sel = self.pl_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        pid = self._playlist_data[idx][0]
        if messagebox.askyesno("确认", "删除这个播放列表？"):
            self.db.delete_playlist(pid)
            self._refresh_playlists()
            self._refresh_library()

    def _add_to_playlist_dialog(self):
        ids = self._get_selected_ids()
        if not ids:
            return
        pls = self.db.list_playlists()
        if not pls:
            messagebox.showinfo("提示", "请先创建播放列表")
            return

        T = self.theme
        dlg = tk.Toplevel(self.root)
        dlg.title("添加到播放列表")
        dlg.geometry("280x220")
        dlg.configure(bg=T["bg"])
        dlg.transient(self.root)
        dlg.grab_set()
        self._center_dialog(dlg)

        tk.Label(dlg, text="选择播放列表", bg=T["bg"], fg=T["dim"],
                 font=F["sm"]).pack(anchor="w", padx=20, pady=(16, 6))

        lb = tk.Listbox(dlg, bg=T["surface"], fg=T["text"],
                        font=F["body"], selectbackground=T["accent"],
                        selectforeground="white", borderwidth=0,
                        highlightthickness=0)
        for p in pls:
            lb.insert("end", f"  {p[1]}")
        lb.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        def _add():
            s = lb.curselection()
            if s:
                pid = pls[s[0]][0]
                for sid in ids:
                    self.db.add_to_playlist(pid, sid)
                self._refresh_playlists()
                dlg.destroy()

        btn = tk.Button(dlg, text="添加", bg=T["accent"], fg="white",
                        font=F["body"], padx=20, pady=4, borderwidth=0,
                        cursor="hand2", command=_add)
        btn.pack(pady=(0, 12))
        _hover(btn, T["accent"], T["accent2"])

    # ═══════════════════════════════════════════════════════════
    # Context menu
    # ═══════════════════════════════════════════════════════════

    def _on_right_click(self, event):
        try:
            self.tree.selection_set(self.tree.identify_row(event.y))
            self.tree_menu.post(event.x_root, event.y_root)
        finally:
            self.tree_menu.grab_release()

    def _edit_tags(self):
        ids = self._get_selected_ids()
        if not ids:
            return
        song = self.db.get_song(ids[0])
        T = self.theme

        dlg = tk.Toplevel(self.root)
        dlg.title("编辑标签")
        dlg.geometry("360x300")
        dlg.configure(bg=T["bg"])
        dlg.transient(self.root)
        self._center_dialog(dlg)

        fields = [
            ("标题", "title", song[2]),
            ("艺术家", "artist", song[3]),
            ("专辑", "album", song[4]),
            ("流派", "genre", song[5]),
            ("年份", "year", str(song[6] or "")),
        ]
        vars_ = {}
        for i, (label, key, val) in enumerate(fields):
            tk.Label(dlg, text=label, bg=T["bg"], fg=T["dim"],
                     font=F["sm"]).grid(row=i, column=0, sticky="w",
                                        padx=(24, 8), pady=(12 if i == 0 else 4, 0))
            v = tk.StringVar(value=val)
            vars_[key] = v
            tk.Entry(dlg, textvariable=v, width=24, bg=T["surface"],
                     fg=T["text"], font=F["body"],
                     insertbackground=T["text"], borderwidth=0,
                     relief="flat").grid(row=i, column=1, padx=(0, 24),
                                         pady=(12 if i == 0 else 4, 0), ipady=3)

        def _save():
            kwargs = {k: v.get() for k, v in vars_.items()}
            try:
                kwargs["year"] = int(kwargs["year"]) if kwargs["year"] else 0
            except ValueError:
                kwargs["year"] = 0
            self.db.update_tags(ids[0], **kwargs)
            self._refresh_library()
            dlg.destroy()

        btn = tk.Button(dlg, text="保存", bg=T["accent"], fg="white",
                        font=F["body"], padx=24, pady=4, borderwidth=0,
                        cursor="hand2", command=_save)
        btn.grid(row=len(fields), column=0, columnspan=2, pady=20)
        _hover(btn, T["accent"], T["accent2"])

    def _delete_selected(self):
        ids = self._get_selected_ids()
        if not ids:
            return
        if messagebox.askyesno("确认", f"从库中删除 {len(ids)} 首歌曲？\n(不会删除文件)"):
            for sid in ids:
                self.db.delete_song(sid)
            self._refresh_library()
            self._refresh_playlists()

    # ═══════════════════════════════════════════════════════════
    # Scanner
    # ═══════════════════════════════════════════════════════════

    def _scan_dir(self):
        folder = filedialog.askdirectory(title="选择音乐文件夹")
        if not folder:
            return

        T = self.theme
        dlg = tk.Toplevel(self.root)
        dlg.title("扫描中")
        dlg.geometry("380x120")
        dlg.configure(bg=T["bg"])
        dlg.transient(self.root)
        self._center_dialog(dlg)

        status_label = tk.Label(dlg, text="正在查找音频文件...",
                                bg=T["bg"], fg=T["text"], font=F["body"])
        status_label.pack(pady=(20, 8))

        prog = ttk.Progressbar(dlg, mode="determinate", length=320)
        prog.pack(pady=(0, 8))

        cancelled = threading.Event()
        cancel_btn = tk.Button(dlg, text="取消", bg=T["surface"], fg=T["text"],
                               borderwidth=0, padx=12, pady=2, font=F["sm"],
                               cursor="hand2", command=cancelled.set)
        cancel_btn.pack()
        dlg.protocol("WM_DELETE_WINDOW", cancelled.set)

        def _scan():
            files = quick_scan(folder)
            total = len(files)
            if total == 0:
                self.root.after(0, lambda: (
                    dlg.destroy(),
                    messagebox.showinfo("扫描", "未发现音频文件")))
                return
            self.root.after(0, lambda: prog.config(maximum=total))
            added = 0

            for i, fp in enumerate(files):
                if cancelled.is_set():
                    break
                meta = probe_file(fp)
                meta.setdefault("file_path", str(Path(fp).resolve()))
                result = self.db.add_song(
                    file_path=meta["file_path"],
                    title=meta["title"] or Path(fp).stem,
                    artist=meta["artist"],
                    album=meta["album"],
                    genre=meta["genre"],
                    year=meta["year"],
                    duration=meta["duration"],
                    fmt=meta["format"],
                    bitrate=meta["bitrate"],
                    sample_rate=meta["sample_rate"],
                    channels=meta["channels"],
                )
                if result:
                    added += 1
                self.root.after(0, lambda i=i, t=total, f=fp:
                                (prog.configure(value=i + 1),
                                 status_label.config(
                                     text=f"[{i+1}/{t}] {Path(f).name[:32]}")))

            count = added
            self.root.after(0, lambda: (
                dlg.destroy(),
                self._refresh_library(),
                self._refresh_playlists(),
                messagebox.showinfo("完成",
                                    f"新增 {count} 首"
                                    + ("（已取消）" if cancelled.is_set() else ""))))

        threading.Thread(target=_scan, daemon=True).start()

    # ═══════════════════════════════════════════════════════════
    # Converter
    # ═══════════════════════════════════════════════════════════

    CONVERT_FORMATS = {
        "mp3":  ["-codec:a", "libmp3lame", "-q:a", "2"],
        "flac": ["-codec:a", "flac"],
        "wav":  [],
        "ogg":  ["-codec:a", "libvorbis", "-q:a", "5"],
        "opus": ["-codec:a", "libopus", "-b:a", "128k"],
        "m4a":  ["-codec:a", "aac", "-b:a", "192k"],
    }

    def _open_converter(self):
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            messagebox.showerror("格式转换", "未找到 ffmpeg。")
            return

        T = self.theme
        dlg = tk.Toplevel(self.root)
        dlg.title("格式转换")
        dlg.geometry("420x280")
        dlg.configure(bg=T["bg"])
        dlg.transient(self.root)
        self._center_dialog(dlg)

        files = []
        file_label = tk.Label(dlg, text="未选择文件", bg=T["bg"],
                              fg=T["dim"], font=F["body"])

        def _pick_files():
            exts = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTS))
            picked = filedialog.askopenfilenames(
                title="选择要转换的音频文件", parent=dlg,
                filetypes=[("音频文件", exts), ("所有文件", "*.*")])
            if picked:
                files.clear()
                files.extend(picked)
                file_label.config(text=f"已选择 {len(files)} 个文件",
                                  fg=T["text"])

        btn_pick = tk.Button(dlg, text="选择文件", bg=T["surface"], fg=T["text"],
                             font=F["body"], padx=16, pady=4, borderwidth=0,
                             cursor="hand2", command=_pick_files)
        btn_pick.pack(pady=(24, 4))
        _hover(btn_pick, T["surface"], T["border"])
        file_label.pack()

        row = tk.Frame(dlg, bg=T["bg"])
        row.pack(pady=12)
        tk.Label(row, text="目标格式", bg=T["bg"], fg=T["dim"],
                 font=F["sm"]).pack(side="left", padx=(0, 8))
        fmt_var = tk.StringVar(value="mp3")
        ttk.Combobox(row, textvariable=fmt_var, state="readonly", width=8,
                     values=list(self.CONVERT_FORMATS)).pack(side="left")

        prog = ttk.Progressbar(dlg, mode="determinate", length=340)
        prog.pack(pady=(4, 2))
        status = tk.Label(dlg, text="", bg=T["bg"], fg=T["dim"], font=F["sm"])
        status.pack()

        def _convert():
            if not files:
                messagebox.showinfo("格式转换", "请先选择文件", parent=dlg)
                return
            out_dir = filedialog.askdirectory(title="选择输出文件夹", parent=dlg)
            if not out_dir:
                return
            fmt = fmt_var.get()
            btn_go.config(state="disabled")
            prog.config(maximum=len(files), value=0)

            def _work():
                done, failed = 0, 0
                for i, src in enumerate(files):
                    dst = str(Path(out_dir) / (Path(src).stem + "." + fmt))
                    self.root.after(0, lambda n=Path(src).name: status.config(
                        text=f"{n[:36]}"))
                    try:
                        r = subprocess.run(
                            [ffmpeg, "-y", "-i", src, "-vn",
                             *self.CONVERT_FORMATS[fmt], dst],
                            capture_output=True, timeout=600,
                            **SUBPROCESS_FLAGS)
                        if r.returncode == 0:
                            done += 1
                        else:
                            failed += 1
                    except Exception:
                        failed += 1
                    self.root.after(0, lambda v=i + 1: prog.config(value=v))

                def _finish():
                    btn_go.config(state="normal")
                    status.config(text=f"完成：{done} 成功，{failed} 失败")
                self.root.after(0, _finish)

            threading.Thread(target=_work, daemon=True).start()

        btn_go = tk.Button(dlg, text="开始转换", bg=T["accent"], fg="white",
                           font=F["body"], padx=20, pady=4, borderwidth=0,
                           cursor="hand2", command=_convert)
        btn_go.pack(pady=8)
        _hover(btn_go, T["accent"], T["accent2"])

    # ═══════════════════════════════════════════════════════════
    # About
    # ═══════════════════════════════════════════════════════════

    def _about_dialog(self):
        T = self.theme
        dlg = tk.Toplevel(self.root)
        dlg.title("关于")
        dlg.geometry("300x200")
        dlg.configure(bg=T["bg"])
        dlg.transient(self.root)
        self._center_dialog(dlg)

        tk.Label(dlg, text=APP_NAME, bg=T["bg"], fg=T["text"],
                 font=F["h1"]).pack(pady=(28, 2))
        tk.Label(dlg, text=f"v{__version__}", bg=T["bg"], fg=T["dim"],
                 font=F["sm"]).pack()
        tk.Label(dlg, text="本地音乐管理 · 播放 · 转换",
                 bg=T["bg"], fg=T["dim"], font=F["sm"]).pack(pady=(12, 0))
        tk.Label(dlg, text="免费开源 · 完全离线 · 零数据收集",
                 bg=T["bg"], fg=T["dim"], font=F["sm"]).pack(pady=(2, 16))

        link = tk.Label(dlg, text="github.com/MeachalLouisJunyan/moe-music-studio",
                        bg=T["bg"], fg=T["accent"], font=F["sm"], cursor="hand2")
        link.pack()
        link.bind("<Button-1>", lambda e: webbrowser.open(REPO_URL))

    # ═══════════════════════════════════════════════════════════
    # Theme
    # ═══════════════════════════════════════════════════════════

    def _toggle_theme(self):
        if self._theme_name == "light":
            self._set_theme("dark")
        else:
            self._set_theme("light")

    def _set_theme(self, name):
        if name not in THEMES:
            return
        self.theme = THEMES[name]
        self._theme_name = name
        save_settings(theme=name)
        self._apply_theme()

    def _apply_theme(self):
        T = self.theme

        self.root.configure(bg=T["bg"])
        self.topbar.configure(bg=T["bg"])
        self.app_title.configure(bg=T["bg"], fg=T["text"])
        self.menu_btn.configure(bg=T["bg"], fg=T["dim"])
        self.theme_btn.configure(bg=T["bg"], fg=T["dim"])
        self.search_frame.configure(bg=T["bg"])
        self.search_entry.configure(bg=T["surface"], fg=T["text"],
                                    insertbackground=T["text"])
        self.top_sep.configure(bg=T["border"])
        self.bottom_sep.configure(bg=T["border"])
        self.side_sep.configure(bg=T["border"])

        self.main.configure(bg=T["bg"])
        self.sidebar.configure(bg=T["bg"])
        for w in self.sidebar.winfo_children():
            try:
                w.configure(bg=T["bg"])
                if hasattr(w, "winfo_children"):
                    for c in w.winfo_children():
                        try:
                            c.configure(bg=T["bg"])
                        except tk.TclError:
                            pass
            except tk.TclError:
                pass

        self._lib_all_btn.configure(bg=T["bg"], fg=T["text"])
        self._lib_recent_btn.configure(bg=T["bg"], fg=T["text"])
        self._pl_add_btn.configure(bg=T["bg"], fg=T["dim"])
        self.pl_listbox.configure(bg=T["bg"], fg=T["text"],
                                  selectbackground=T["surface"],
                                  selectforeground=T["text"])
        self.count_label.configure(bg=T["bg"], fg=T["dim"])

        self.player_frame.configure(bg=T["surface"])
        self.art_label.configure(bg=T["border"])
        self.np_title.configure(bg=T["surface"], fg=T["text"])
        self.np_artist.configure(bg=T["surface"], fg=T["dim"])
        for btn in (self.btn_prev, self.btn_play, self.btn_next):
            btn.configure(bg=T["surface"], fg=T["text"],
                          activebackground=T["surface"],
                          activeforeground=T["accent"])
        self.seek_scale.configure(bg=T["surface"], fg=T["progress"],
                                  troughcolor=T["border"])
        self.time_label.configure(bg=T["surface"], fg=T["dim"])
        self.vol_scale.configure(bg=T["surface"], troughcolor=T["border"])

        # Update ttk styles
        style = ttk.Style()
        style.configure("Treeview",
                        background=T["bg"], foreground=T["text"],
                        fieldbackground=T["bg"])
        style.configure("Treeview.Heading",
                        background=T["bg"], foreground=T["dim"])
        style.map("Treeview",
                  background=[("selected", T["accent"])],
                  foreground=[("selected", "#ffffff")])

        # Re-bind hovers
        _hover(self.menu_btn, T["bg"], T["surface"])
        _hover(self.theme_btn, T["bg"], T["surface"])
        _hover(self._lib_all_btn, T["bg"], T["surface"])
        _hover(self._lib_recent_btn, T["bg"], T["surface"])
        _hover(self._pl_add_btn, T["bg"], T["surface"])

    # ═══════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════

    def _center_dialog(self, dlg):
        dlg.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dlg.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")


# ═══════════════════════════════════════════════════════════════
# Entry
# ═══════════════════════════════════════════════════════════════

def main():
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()

    JyMusic(root)
    root.mainloop()


if __name__ == "__main__":
    main()

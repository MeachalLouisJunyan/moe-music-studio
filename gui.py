#!/usr/bin/env python3
"""
Moe Music Studio — GUI
Music library manager + player + converter — all in one.
"""

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).parent))

from database import MusicDB
from player import get_player
from scanner import probe_file, quick_scan, SUPPORTED_EXTS

# ═══════════════════════════════════════════════════════════════
# Themes
# ═══════════════════════════════════════════════════════════════

THEMES = {
    "anime": {
        "bg":       "#fff0f5",
        "surface":  "#ffe4ec",
        "card":     "#ffffff",
        "border":   "#f5c6d0",
        "text":     "#4a2040",
        "dim":      "#b8869e",
        "accent":   "#ff6b9d",
        "accent2":  "#c084fc",
        "green":    "#86dba6",
        "red":      "#ff6b6b",
        "yellow":   "#f5c842",
        "progress": "#ff6b9d",
    },
    "dark": {
        "bg":       "#0d0d14",
        "surface":  "#171724",
        "card":     "#1e1e30",
        "border":   "#2a2a3c",
        "text":     "#e2e2ed",
        "dim":      "#6b6b80",
        "accent":   "#818cf8",
        "accent2":  "#a5b4fc",
        "green":    "#4ade80",
        "red":      "#f87171",
        "yellow":   "#fbbf24",
        "progress": "#818cf8",
    },
    "light": {
        "bg":       "#f5f5f5",
        "surface":  "#e8e8e8",
        "card":     "#ffffff",
        "border":   "#d4d4d4",
        "text":     "#1a1a2e",
        "dim":      "#888888",
        "accent":   "#6366f1",
        "accent2":  "#818cf8",
        "green":    "#22c55e",
        "red":      "#ef4444",
        "yellow":   "#eab308",
        "progress": "#6366f1",
    },
}


# ═══════════════════════════════════════════════════════════════
# App
# ═══════════════════════════════════════════════════════════════

class MoeMusicStudio:
    def __init__(self, root):
        self.root = root
        self.root.title("Moe Music Studio")
        self.root.geometry("1024x640")
        self.root.minsize(800, 500)

        self.db = MusicDB(str(Path(__file__).parent / "music.db"))
        self.player = get_player()
        self.theme = THEMES["anime"]
        self.current_playlist = None  # playlist id for queue
        self.play_queue = []          # list of song ids in order
        self.queue_index = -1

        self.root.configure(bg=self.theme["bg"])
        self._build_ui()
        self._refresh_library()
        self._refresh_playlists()
        self._update_player_ui()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self.player.stop()
        self.db.close()
        self.root.destroy()

    # ═══════════════════════════════════════════════════════════
    # UI Build
    # ═══════════════════════════════════════════════════════════

    def _build_ui(self):
        T = self.theme
        F = {
            "h1":   ("Microsoft YaHei UI", 14, "bold"),
            "h2":   ("Microsoft YaHei UI", 11, "bold"),
            "body": ("Microsoft YaHei UI", 10),
            "sm":   ("Microsoft YaHei UI", 9),
            "mono": ("Consolas", 10),
        }

        # ── Menubar ──
        menubar = tk.Menu(self.root, bg=T["card"], fg=T["text"],
                          activebackground=T["accent"],
                          activeforeground="white",
                          font=("Microsoft YaHei UI", 9))
        file_menu = tk.Menu(menubar, tearoff=0, bg=T["card"], fg=T["text"],
                            activebackground=T["accent"])
        file_menu.add_command(label="扫描文件夹...", command=self._scan_dir)
        file_menu.add_separator()
        file_menu.add_command(label="格式转换...", command=self._open_converter)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_close)
        menubar.add_cascade(label="文件", menu=file_menu)

        theme_menu = tk.Menu(menubar, tearoff=0, bg=T["card"], fg=T["text"],
                             activebackground=T["accent"])
        theme_menu.add_command(label="二次元", command=lambda: self._set_theme("anime"))
        theme_menu.add_command(label="暗黑", command=lambda: self._set_theme("dark"))
        theme_menu.add_command(label="明亮", command=lambda: self._set_theme("light"))
        menubar.add_cascade(label="主题", menu=theme_menu)

        play_menu = tk.Menu(menubar, tearoff=0, bg=T["card"], fg=T["text"],
                            activebackground=T["accent"])
        play_menu.add_command(label="新建播放列表",
                              command=self._new_playlist_dialog)
        menubar.add_cascade(label="播放列表", menu=play_menu)
        self.root.config(menu=menubar)

        # ── Main layout ──
        main = tk.Frame(self.root, bg=T["bg"])
        main.pack(fill="both", expand=True, padx=6, pady=(0, 2))

        # ---- Left sidebar (playlists) ----
        self.sidebar = tk.Frame(main, bg=T["surface"], width=200)
        self.sidebar.pack(side="left", fill="y", padx=(0, 6))
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="播放列表", fg=T["text"], bg=T["surface"],
                 font=F["h2"]).pack(anchor="w", padx=10, pady=(8, 4))

        pl_btns = tk.Frame(self.sidebar, bg=T["surface"])
        pl_btns.pack(fill="x", padx=6, pady=(0, 4))
        tk.Button(pl_btns, text="+ 新建", bg=T["accent"], fg="white",
                  font=F["sm"], padx=10, pady=2, borderwidth=0,
                  command=self._new_playlist_dialog,
                  cursor="hand2").pack(side="left")
        tk.Button(pl_btns, text="删除", bg=T["dim"], fg="white",
                  font=F["sm"], padx=10, pady=2, borderwidth=0,
                  command=self._delete_playlist,
                  cursor="hand2").pack(side="right")

        pl_container = tk.Frame(self.sidebar, bg=T["surface"])
        pl_container.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        self.pl_listbox = tk.Listbox(
            pl_container, bg=T["surface"], fg=T["text"],
            font=F["body"], selectbackground=T["accent"],
            selectforeground="white", borderwidth=0,
            highlightthickness=0, activestyle="none",
        )
        self.pl_listbox.pack(side="left", fill="both", expand=True)
        self.pl_listbox.bind("<<ListboxSelect>>", self._on_playlist_select)
        self.pl_listbox.bind("<Double-Button-1>", self._play_playlist)

        # ---- Right content area ----
        content = tk.Frame(main, bg=T["bg"])
        content.pack(side="left", fill="both", expand=True)

        # Search
        search_frame = tk.Frame(content, bg=T["bg"])
        search_frame.pack(fill="x", pady=(0, 6))

        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self._on_search())
        tk.Entry(search_frame, textvariable=self.search_var, width=40,
                 bg=T["card"], fg=T["text"], insertbackground=T["text"],
                 font=F["body"], borderwidth=1,
                 relief="solid").pack(side="left", ipady=3, fill="x",
                                      expand=True)

        tk.Button(search_frame, text="搜索", bg=T["accent"], fg="white",
                  font=F["body"], padx=14, pady=3, borderwidth=0,
                  command=self._on_search,
                  cursor="hand2").pack(side="left", padx=(4, 0))

        # Song count
        self.count_label = tk.Label(content, text="", fg=T["dim"], bg=T["bg"],
                                    font=F["sm"], anchor="w")
        self.count_label.pack(fill="x", pady=(0, 2))

        # Song list (Treeview)
        columns = ("title", "artist", "album", "duration", "format")
        self.tree = ttk.Treeview(content, columns=columns,
                                 show="headings", selectmode="extended")
        self.tree.heading("title", text="标题")
        self.tree.heading("artist", text="艺术家")
        self.tree.heading("album", text="专辑")
        self.tree.heading("duration", text="时长")
        self.tree.heading("format", text="格式")

        self.tree.column("title", width=280)
        self.tree.column("artist", width=160)
        self.tree.column("album", width=160)
        self.tree.column("duration", width=70, anchor="center")
        self.tree.column("format", width=60, anchor="center")

        self.tree.pack(fill="both", expand=True)

        # Style treeview
        tree_style = ttk.Style()
        tree_style.theme_use("clam")
        tree_style.configure("Treeview",
                             background=T["card"],
                             foreground=T["text"],
                             fieldbackground=T["card"],
                             font=F["body"],
                             rowheight=26)
        tree_style.configure("Treeview.Heading",
                             background=T["surface"],
                             foreground=T["dim"],
                             font=F["body"])
        tree_style.map("Treeview",
                       background=[("selected", T["accent"])],
                       foreground=[("selected", "white")])

        # Treeview context menu
        self.tree_menu = tk.Menu(self.root, tearoff=0, bg=T["card"],
                                 fg=T["text"],
                                 activebackground=T["accent"])
        self.tree_menu.add_command(label="播放",
                                   command=self._play_selected)
        self.tree_menu.add_command(label="添加到播放列表",
                                   command=self._add_to_playlist_dialog)
        self.tree_menu.add_command(label="编辑标签",
                                   command=self._edit_tags)
        self.tree_menu.add_separator()
        self.tree_menu.add_command(label="从库中删除",
                                   command=self._delete_selected)
        self.tree.bind("<Button-3>", self._on_right_click)
        self.tree.bind("<Double-1>", lambda e: self._play_selected())

        # ── Player bar (bottom) ──
        player_frame = tk.Frame(self.root, bg=T["surface"], height=56)
        player_frame.pack(fill="x", side="bottom")
        player_frame.pack_propagate(False)

        # Now playing label
        self.np_label = tk.Label(player_frame, text="♫ 未播放",
                                 fg=T["dim"], bg=T["surface"],
                                 font=F["body"], anchor="w", width=40)
        self.np_label.pack(side="left", padx=12)

        # Controls
        ctrl_frame = tk.Frame(player_frame, bg=T["surface"])
        ctrl_frame.pack(side="left", expand=True)

        btn_config = {"bg": T["surface"], "fg": T["text"],
                      "font": ("Segoe UI Symbol", 14),
                      "borderwidth": 0, "cursor": "hand2",
                      "padx": 8, "pady": 2,
                      "activebackground": T["accent"],
                      "activeforeground": "white"}

        self.btn_prev = tk.Button(ctrl_frame, text="⏮", command=self._prev,
                                  **btn_config)
        self.btn_prev.pack(side="left")

        self.btn_play = tk.Button(ctrl_frame, text="▶", command=self._play_pause,
                                  **btn_config)
        self.btn_play.pack(side="left", padx=2)

        self.btn_next = tk.Button(ctrl_frame, text="⏭", command=self._next,
                                  **btn_config)
        self.btn_next.pack(side="left")

        # Volume
        tk.Label(player_frame, text="🔊", fg=T["dim"], bg=T["surface"],
                 font=F["sm"]).pack(side="left", padx=(16, 0))
        self.vol_scale = tk.Scale(
            player_frame, from_=0, to=100, orient="horizontal",
            command=self._on_volume, length=100, showvalue=0,
            bg=T["surface"], fg=T["text"], troughcolor=T["card"],
            highlightthickness=0, borderwidth=0,
        )
        self.vol_scale.set(100)
        self.vol_scale.pack(side="left")

        # Progress
        self.time_label = tk.Label(player_frame, text="00:00 / 00:00",
                                   fg=T["dim"], bg=T["surface"],
                                   font=F["sm"])
        self.time_label.pack(side="right", padx=12)

        # Seek bar
        self.seek_var = tk.DoubleVar()
        self.seek_scale = tk.Scale(
            self.root, from_=0, to=1000, orient="horizontal",
            variable=self.seek_var, command=self._on_seek,
            bg=T["bg"], fg=T["progress"], troughcolor=T["card"],
            highlightthickness=0, borderwidth=0, length=600,
            showvalue=0,
        )
        self.seek_scale.pack(fill="x", side="bottom", padx=6, pady=(0, 0))

        # Playback update timer
        self._update_timer()

    # ═══════════════════════════════════════════════════════════
    # Library
    # ═══════════════════════════════════════════════════════════

    def _refresh_library(self, songs=None):
        self.tree.delete(*self.tree.get_children())
        if songs is None:
            songs = self.db.get_all_songs()

        for s in songs:
            dur = s[6]  # duration
            dur_str = f"{int(dur//60):02d}:{int(dur%60):02d}" if dur else "--:--"
            self.tree.insert("", "end", iid=str(s[0]),
                             values=(s[2], s[3], s[4], dur_str, s[7]))

        count = len(songs) if songs else self.db.count_songs()
        self.count_label.config(text=f"共 {count} 首歌曲")

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

        def on_end(event_type):
            if event_type == "ended":
                self.root.after(0, self._next)

        ok = self.player.play(file_path, song_id, on_end)
        if ok:
            self.np_label.config(
                text=f"♫ {title}",
                fg=self.theme["accent"])
            self._update_player_ui()

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
                    dur = s[6]
                    if dur:
                        self.player.seek(float(val) / 1000 * dur)
        except Exception:
            pass

    def _update_player_ui(self):
        if self.player.is_playing:
            if self.player.is_paused:
                self.btn_play.config(text="▶")
                self.np_label.config(fg=self.theme["yellow"])
            else:
                self.btn_play.config(text="⏸")
                self.np_label.config(fg=self.theme["accent"])
        else:
            self.btn_play.config(text="▶")
            self.np_label.config(fg=self.theme["dim"])

    def _update_timer(self):
        if self.player.is_playing and not self.player.is_paused:
            pos = self.player.get_pos()
            song = self.player.current
            dur = 0
            if song:
                s = self.db.get_song(song[0])
                if s:
                    dur = s[6]
            if dur > 0 and pos < dur:
                self.time_label.config(
                    text=f"{int(pos//60):02d}:{int(pos%60):02d} / "
                         f"{int(dur//60):02d}:{int(dur%60):02d}")
                self.seek_var.set(pos / dur * 1000)
        self.root.after(500, self._update_timer)

    # ═══════════════════════════════════════════════════════════
    # Playlists
    # ═══════════════════════════════════════════════════════════

    def _refresh_playlists(self):
        self.pl_listbox.delete(0, "end")
        self._playlist_data = self.db.list_playlists()
        for p in self._playlist_data:
            name = f"{p[1]}  ({p[3]})"
            self.pl_listbox.insert("end", name)

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
        dlg = tk.Toplevel(self.root)
        dlg.title("新建播放列表")
        dlg.geometry("300x120")
        dlg.configure(bg=self.theme["card"])
        dlg.transient(self.root)
        dlg.grab_set()

        tk.Label(dlg, text="播放列表名称:", bg=self.theme["card"],
                 fg=self.theme["text"], font=("Microsoft YaHei UI", 10)
                 ).pack(pady=(16, 4))
        var = tk.StringVar()
        tk.Entry(dlg, textvariable=var, width=25, bg=self.theme["surface"],
                 fg=self.theme["text"], font=("Microsoft YaHei UI", 10),
                 insertbackground=self.theme["text"]
                 ).pack(pady=(0, 10))
        tk.Button(dlg, text="创建", bg=self.theme["accent"], fg="white",
                  command=lambda: self._create_playlist(var.get(), dlg),
                  padx=20, pady=4, borderwidth=0,
                  font=("Microsoft YaHei UI", 10),
                  cursor="hand2").pack()

    def _create_playlist(self, name, dlg):
        if name.strip():
            self.db.create_playlist(name.strip())
            self._refresh_playlists()
            self._refresh_library()
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

        dlg = tk.Toplevel(self.root)
        dlg.title("添加到播放列表")
        dlg.geometry("300x200")
        dlg.configure(bg=self.theme["card"])
        dlg.transient(self.root)
        dlg.grab_set()

        tk.Label(dlg, text="选择播放列表:", bg=self.theme["card"],
                 fg=self.theme["text"],
                 font=("Microsoft YaHei UI", 10)).pack(pady=(14, 6))

        lb = tk.Listbox(dlg, bg=self.theme["surface"], fg=self.theme["text"],
                        font=("Microsoft YaHei UI", 10),
                        selectbackground=self.theme["accent"])
        for p in pls:
            lb.insert("end", p[1])
        lb.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        def _add():
            s = lb.curselection()
            if s:
                pid = pls[s[0]][0]
                for sid in ids:
                    self.db.add_to_playlist(pid, sid)
                self._refresh_playlists()
                dlg.destroy()

        tk.Button(dlg, text="添加", bg=self.theme["accent"], fg="white",
                  command=_add, padx=20, pady=4, borderwidth=0,
                  font=("Microsoft YaHei UI", 10),
                  cursor="hand2").pack()

    # ═══════════════════════════════════════════════════════════
    # Context menu actions
    # ═══════════════════════════════════════════════════════════

    def _on_right_click(self, event):
        try:
            self.tree.selection_set(
                self.tree.identify_row(event.y))
            self.tree_menu.post(event.x_root, event.y_root)
        finally:
            self.tree_menu.grab_release()

    def _edit_tags(self):
        ids = self._get_selected_ids()
        if not ids:
            return
        song = self.db.get_song(ids[0])

        dlg = tk.Toplevel(self.root)
        dlg.title("编辑标签")
        dlg.geometry("360x280")
        dlg.configure(bg=self.theme["card"])
        dlg.transient(self.root)

        fields = [
            ("标题", "title", song[2]),
            ("艺术家", "artist", song[3]),
            ("专辑", "album", song[4]),
            ("流派", "genre", song[5]),
            ("年份", "year", str(song[6] or "")),
        ]
        vars_ = {}
        for i, (label, key, val) in enumerate(fields):
            tk.Label(dlg, text=label, bg=self.theme["card"],
                     fg=self.theme["text"],
                     font=("Microsoft YaHei UI", 10)
                     ).grid(row=i, column=0, sticky="w", padx=16,
                            pady=(10 if i == 0 else 2, 2))
            v = tk.StringVar(value=val)
            vars_[key] = v
            tk.Entry(dlg, textvariable=v, width=25,
                     bg=self.theme["surface"], fg=self.theme["text"],
                     font=("Microsoft YaHei UI", 10),
                     insertbackground=self.theme["text"]
                     ).grid(row=i, column=1, padx=8,
                            pady=(10 if i == 0 else 2, 2))

        def _save():
            kwargs = {k: v.get() for k, v in vars_.items()}
            try:
                kwargs["year"] = int(kwargs["year"]) if kwargs["year"] else 0
            except ValueError:
                kwargs["year"] = 0
            self.db.update_tags(ids[0], **kwargs)
            self._refresh_library()
            dlg.destroy()

        tk.Button(dlg, text="保存", bg=self.theme["accent"], fg="white",
                  command=_save, padx=24, pady=6, borderwidth=0,
                  font=("Microsoft YaHei UI", 10),
                  cursor="hand2").grid(row=len(fields), column=0,
                                       columnspan=2, pady=16)

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

        dlg = tk.Toplevel(self.root)
        dlg.title("扫描中...")
        dlg.geometry("360x100")
        dlg.configure(bg=self.theme["card"])
        dlg.transient(self.root)

        status_label = tk.Label(dlg, text="正在扫描...",
                                bg=self.theme["card"],
                                fg=self.theme["text"],
                                font=("Microsoft YaHei UI", 10))
        status_label.pack(pady=(20, 8))

        prog = ttk.Progressbar(dlg, mode="determinate", length=300)
        prog.pack(pady=(0, 16))

        def _scan():
            files = quick_scan(folder)
            total = len(files)
            prog.config(maximum=total)

            for i, fp in enumerate(files):
                meta = probe_file(fp)
                self.db.add_song(
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
                self.root.after(0, lambda i=i, t=total, f=fp:
                                (prog.configure(value=i + 1),
                                 status_label.config(
                                     text=f"扫描中... [{i+1}/{t}] "
                                          f"{Path(f).name[:30]}")))
            self.root.after(0, lambda: (dlg.destroy(),
                                         self._refresh_library(),
                                         self._refresh_playlists()))

        threading.Thread(target=_scan, daemon=True).start()

    # ═══════════════════════════════════════════════════════════
    # Converter (opens converter tool)
    # ═══════════════════════════════════════════════════════════

    def _open_converter(self):
        converter_path = (Path(__file__).parent.parent /
                          "audio-converter" / "audio_convert_gui_anime.py")
        if converter_path.is_file():
            threading.Thread(
                target=lambda: os.system(
                    f'start python "{converter_path}"'),
                daemon=True).start()
        else:
            messagebox.showinfo("提示",
                                "未找到转换器\n"
                                "请确保 audio-converter 在同级目录")

    # ═══════════════════════════════════════════════════════════
    # Theme
    # ═══════════════════════════════════════════════════════════

    def _set_theme(self, name):
        self.theme = THEMES[name]
        self.root.configure(bg=self.theme["bg"])
        messagebox.showinfo("主题", f"已切换到 {name} 主题\n重启后全局生效")


# ═══════════════════════════════════════════════════════════════
# Entry
# ═══════════════════════════════════════════════════════════════

def main():
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()

    MoeMusicStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()

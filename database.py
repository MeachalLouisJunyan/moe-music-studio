#!/usr/bin/env python3
"""Music library database layer."""

import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS songs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path       TEXT UNIQUE NOT NULL,
    title           TEXT DEFAULT '',
    artist          TEXT DEFAULT '',
    album           TEXT DEFAULT '',
    genre           TEXT DEFAULT '',
    year            INTEGER DEFAULT 0,
    duration        REAL DEFAULT 0,
    format          TEXT DEFAULT '',
    bitrate         INTEGER DEFAULT 0,
    sample_rate     INTEGER DEFAULT 0,
    channels        INTEGER DEFAULT 0,
    date_added      REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS playlists (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL,
    created REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS playlist_songs (
    playlist_id INTEGER NOT NULL,
    song_id     INTEGER NOT NULL,
    position    INTEGER DEFAULT 0,
    PRIMARY KEY (playlist_id, song_id),
    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
    FOREIGN KEY (song_id)     REFERENCES songs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(artist);
CREATE INDEX IF NOT EXISTS idx_songs_album  ON songs(album);
CREATE INDEX IF NOT EXISTS idx_songs_genre  ON songs(genre);
CREATE INDEX IF NOT EXISTS idx_pls_pos      ON playlist_songs(playlist_id, position);
"""

ALLOWED_TAG_FIELDS = {"title", "artist", "album", "genre", "year"}


class MusicDB:
    def __init__(self, db_path="music.db"):
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ── Songs ────────────────────────────────────────────────

    def add_song(self, file_path, title="", artist="", album="",
                 genre="", year=0, duration=0.0, fmt="",
                 bitrate=0, sample_rate=0, channels=0):
        with self._lock:
            try:
                cur = self.conn.execute(
                    "INSERT INTO songs (file_path, title, artist, album, "
                    "genre, year, duration, format, bitrate, sample_rate, "
                    "channels, date_added) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (file_path, title, artist, album, genre, year,
                     duration, fmt, bitrate, sample_rate, channels,
                     time.time()))
                self.conn.commit()
                return cur.lastrowid
            except sqlite3.IntegrityError:
                return None

    def get_all_songs(self, order="date_added DESC"):
        with self._lock:
            return self.conn.execute(
                f"SELECT * FROM songs ORDER BY {order}"
            ).fetchall()

    def search(self, query):
        q = f"%{query}%"
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM songs WHERE title LIKE ? OR artist LIKE ? "
                "OR album LIKE ? OR genre LIKE ? ORDER BY artist, album",
                (q, q, q, q)).fetchall()

    def get_by_artist(self, artist):
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM songs WHERE artist=? ORDER BY album, title",
                (artist,)).fetchall()

    def get_artists(self):
        with self._lock:
            rows = self.conn.execute(
                "SELECT DISTINCT artist FROM songs WHERE artist!='' "
                "ORDER BY artist").fetchall()
            return [r[0] for r in rows]

    def get_albums(self):
        with self._lock:
            rows = self.conn.execute(
                "SELECT DISTINCT album FROM songs WHERE album!='' "
                "ORDER BY album").fetchall()
            return [r[0] for r in rows]

    def get_genres(self):
        with self._lock:
            rows = self.conn.execute(
                "SELECT DISTINCT genre FROM songs WHERE genre!='' "
                "ORDER BY genre").fetchall()
            return [r[0] for r in rows]

    def get_song(self, song_id):
        with self._lock:
            return self.conn.execute(
                "SELECT * FROM songs WHERE id=?", (song_id,)).fetchone()

    def delete_song(self, song_id):
        with self._lock:
            self.conn.execute("DELETE FROM songs WHERE id=?", (song_id,))
            self.conn.commit()

    def update_tags(self, song_id, **kwargs):
        filtered = {k: v for k, v in kwargs.items()
                    if k in ALLOWED_TAG_FIELDS}
        if not filtered:
            return
        sets = ", ".join(f"{k}=?" for k in filtered)
        with self._lock:
            self.conn.execute(
                f"UPDATE songs SET {sets} WHERE id=?",
                (*filtered.values(), song_id))
            self.conn.commit()

    def count_songs(self):
        with self._lock:
            return self.conn.execute(
                "SELECT COUNT(*) FROM songs").fetchone()[0]

    # ── Playlists ────────────────────────────────────────────

    def create_playlist(self, name):
        with self._lock:
            cur = self.conn.execute(
                "INSERT INTO playlists (name, created) VALUES (?, ?)",
                (name, time.time()))
            self.conn.commit()
            return cur.lastrowid

    def list_playlists(self):
        with self._lock:
            return self.conn.execute(
                "SELECT p.id, p.name, p.created, COUNT(ps.song_id) "
                "FROM playlists p LEFT JOIN playlist_songs ps "
                "ON p.id = ps.playlist_id GROUP BY p.id "
                "ORDER BY p.name").fetchall()

    def rename_playlist(self, pid, name):
        with self._lock:
            self.conn.execute(
                "UPDATE playlists SET name=? WHERE id=?", (name, pid))
            self.conn.commit()

    def delete_playlist(self, pid):
        with self._lock:
            self.conn.execute("DELETE FROM playlists WHERE id=?", (pid,))
            self.conn.commit()

    def add_to_playlist(self, pid, song_id):
        with self._lock:
            max_pos = self.conn.execute(
                "SELECT COALESCE(MAX(position), -1) FROM playlist_songs "
                "WHERE playlist_id=?", (pid,)).fetchone()[0]
            try:
                self.conn.execute(
                    "INSERT OR IGNORE INTO playlist_songs "
                    "(playlist_id, song_id, position) VALUES (?,?,?)",
                    (pid, song_id, max_pos + 1))
                self.conn.commit()
            except sqlite3.IntegrityError:
                pass

    def remove_from_playlist(self, pid, song_id):
        with self._lock:
            self.conn.execute(
                "DELETE FROM playlist_songs WHERE playlist_id=? AND song_id=?",
                (pid, song_id))
            self.conn.commit()

    def get_playlist_songs(self, pid):
        with self._lock:
            return self.conn.execute(
                "SELECT s.* FROM songs s JOIN playlist_songs ps "
                "ON s.id = ps.song_id WHERE ps.playlist_id=? "
                "ORDER BY ps.position", (pid,)).fetchall()

    def get_playlist_name(self, pid):
        with self._lock:
            row = self.conn.execute(
                "SELECT name FROM playlists WHERE id=?", (pid,)).fetchone()
            return row[0] if row else ""

    def export_playlist(self, pid):
        """Return list of file_paths for a playlist."""
        songs = self.get_playlist_songs(pid)
        return [s[1] for s in songs]  # file_path is index 1

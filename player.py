#!/usr/bin/env python3
"""Audio player using pygame.mixer — zero external deps beyond pygame."""

import threading
import time

_player = None


def get_player():
    global _player
    if _player is None:
        _player = _AudioPlayer()
    return _player


class _AudioPlayer:

    def __init__(self):
        self._current = None       # (song_id, file_path)
        self._playing = False
        self._paused = False
        self._volume = 1.0
        self._callback = None
        self._init_pygame()

    def _init_pygame(self):
        import pygame
        self._pygame = pygame
        self._mixer_ok = False
        try:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2,
                                  buffer=4096)
            except Exception:
                pygame.mixer.init()
            self._mixer_ok = True
        except Exception:
            # No usable audio device — keep the app usable (library,
            # tags, converter); playback just stays off.
            return
        pygame.mixer.music.set_endevent(pygame.USEREVENT + 1)
        self._end_event = pygame.USEREVENT + 1
        threading.Thread(target=self._event_loop, daemon=True).start()

    def _event_loop(self):
        while True:
            try:
                for event in self._pygame.event.get():
                    if event.type == self._end_event:
                        self._playing = False
                        self._paused = False
                        if self._callback:
                            self._callback("ended")
            except Exception:
                pass
            time.sleep(0.2)

    def play(self, file_path, song_id=None, on_end=None):
        if not self._mixer_ok:
            return False
        self._callback = on_end
        try:
            self._pygame.mixer.music.load(file_path)
            self._pygame.mixer.music.play()
            self._playing = True
            self._paused = False
            self._current = (song_id, file_path)
            return True
        except Exception:
            return False

    def pause(self):
        if self._playing and not self._paused:
            self._pygame.mixer.music.pause()
            self._paused = True

    def resume(self):
        if self._paused:
            self._pygame.mixer.music.unpause()
            self._paused = False

    def toggle(self):
        if self._playing:
            if self._paused:
                self.resume()
            else:
                self.pause()

    def stop(self):
        if self._mixer_ok:
            self._pygame.mixer.music.stop()
        self._playing = False
        self._paused = False
        self._current = None

    def set_volume(self, vol):
        self._volume = max(0.0, min(1.0, vol))
        if self._mixer_ok:
            self._pygame.mixer.music.set_volume(self._volume)

    @property
    def volume(self):
        return self._volume

    @property
    def is_playing(self):
        return self._playing

    @property
    def is_paused(self):
        return self._paused

    @property
    def current(self):
        return self._current

    def get_pos(self):
        """Position in seconds."""
        try:
            return self._pygame.mixer.music.get_pos() / 1000.0
        except Exception:
            return 0

    def seek(self, seconds):
        try:
            self._pygame.mixer.music.set_pos(seconds)
        except Exception:
            pass

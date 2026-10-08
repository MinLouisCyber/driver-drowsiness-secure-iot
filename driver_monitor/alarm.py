from __future__ import annotations

import threading


class Alarm:
    def __init__(self, pin: int = 18) -> None:
        self._buzzer = None
        self._active = False
        self._enabled = threading.Event()
        self._stopped = threading.Event()
        self._sound_thread: threading.Thread | None = None
        try:
            from gpiozero import Buzzer

            self._buzzer = Buzzer(pin)
        except Exception:
            self._buzzer = None
            try:
                import winsound

                self._winsound = winsound
                self._sound_thread = threading.Thread(
                    target=self._sound_loop,
                    name="drowsiness-alarm",
                    daemon=True,
                )
                self._sound_thread.start()
            except Exception:
                self._winsound = None

    def _sound_loop(self) -> None:
        while not self._stopped.is_set():
            if not self._enabled.wait(0.1):
                continue
            if self._stopped.is_set():
                break
            self._winsound.Beep(1800, 300)
            self._stopped.wait(0.12)

    def set(self, active: bool) -> None:
        if active == self._active:
            return
        self._active = active
        if self._buzzer is not None:
            self._buzzer.on() if active else self._buzzer.off()
        elif self._sound_thread is not None:
            self._enabled.set() if active else self._enabled.clear()
        print("ALARM ON" if active else "ALARM OFF")

    def close(self) -> None:
        self.set(False)
        if self._buzzer is not None:
            self._buzzer.close()
        if self._sound_thread is not None:
            self._stopped.set()
            self._enabled.set()
            self._sound_thread.join(timeout=1.0)

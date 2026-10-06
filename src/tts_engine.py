"""Best-effort Android Native TTS with desktop and offline fallbacks."""
from __future__ import annotations
import logging
import threading

log=logging.getLogger(__name__)
class TTSEngine:
    def __init__(self, language="ar-EG", rate=0.9):
        self.language=language; self.rate=rate; self._engine=None; self._lock=threading.Lock(); self._init()
    def _init(self):
        try:
            from jnius import autoclass
            PythonActivity=autoclass("org.kivy.android.PythonActivity"); Locale=autoclass("java.util.Locale"); TextToSpeech=autoclass("android.speech.tts.TextToSpeech")
            self._engine=TextToSpeech(PythonActivity.mActivity, None); self._engine.setLanguage(Locale("ar","EG")); self._engine.setSpeechRate(float(self.rate)); return
        except Exception as exc: log.debug("Android TTS unavailable: %s",exc)
        try:
            import pyttsx3
            self._engine=pyttsx3.init(); self._engine.setProperty("rate",115)
        except Exception as exc: log.info("Desktop TTS unavailable: %s",exc)
    def speak(self,text:str):
        if not text or not self._engine: return
        def run():
            with self._lock:
                try:
                    if self._engine.__class__.__module__.startswith("jnius"):
                        self._engine.speak(text, 0, None, "voice_workout")
                    else:
                        self._engine.say(text); self._engine.runAndWait()
                except Exception: log.exception("TTS failed")
        threading.Thread(target=run,daemon=True).start()
    def stop(self):
        try:
            if self._engine: self._engine.stop()
        except Exception: log.debug("TTS stop failed",exc_info=True)

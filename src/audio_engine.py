"""Offline Vosk microphone recognizer with strict Arabic command grammar."""
from __future__ import annotations
import json, logging, queue, threading
from pathlib import Path
from typing import Callable
log=logging.getLogger(__name__)
ALLOWED_WORDS=["واحد","اتنين","تلاتة","اربعة","خمسة","ستة","سبعة","ثمانية","تسعة","عشرة","حداشر","اتناشر","تلاتاشر","اربعتاشر","خمستاشر","ستاشر","سبعتاشر","تمنتاشر","تسعتاشر","عشرين","واحد وعشرين","اتنين وعشرين","تلاتة وعشرين","اربعة وعشرين","خمسة وعشرين","عدة","تم","عد","كمان","بريك","خلصت","تمام","جاهز","ابدأ"]
class AudioEngine:
    def __init__(self, model_path:str|Path, on_text:Callable[[str],None], on_status:Callable[[str],None]|None=None):
        self.model_path=Path(model_path); self.on_text=on_text; self.on_status=on_status or (lambda _:None); self._stop=threading.Event(); self._thread=None; self._audio_queue=queue.Queue(maxsize=20)
    def start(self):
        if self._thread and self._thread.is_alive(): return
        self._stop.clear(); self._thread=threading.Thread(target=self._run,daemon=True); self._thread.start()
    def stop(self): self._stop.set()
    def _run(self):
        try:
            from vosk import Model, KaldiRecognizer
            import sounddevice as sd
            if not self.model_path.exists(): raise FileNotFoundError(f"Vosk model not found: {self.model_path}")
            model=Model(str(self.model_path)); grammar=json.dumps(ALLOWED_WORDS+ ["[unk]"],ensure_ascii=False); recognizer=KaldiRecognizer(model,16000,grammar)
            def callback(indata,frames,time_info,status):
                if status: log.warning("Audio status: %s",status)
                try: self._audio_queue.put_nowait(bytes(indata))
                except queue.Full: pass
            self.on_status("الميكروفون يعمل")
            with sd.RawInputStream(samplerate=16000,blocksize=8000,dtype="int16",channels=1,callback=callback):
                while not self._stop.is_set():
                    try: data=self._audio_queue.get(timeout=.25)
                    except queue.Empty: continue
                    if recognizer.AcceptWaveform(data):
                        text=json.loads(recognizer.Result()).get("text","").strip()
                        if text: self.on_text(text)
        except Exception as exc:
            log.warning("Audio recognition unavailable: %s",exc); self.on_status(f"الصوت غير متاح: {exc}")

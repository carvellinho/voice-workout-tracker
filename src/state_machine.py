"""Deterministic workout state machine and Arabic voice command handling."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import threading
import time
from typing import Callable, Optional

class WorkoutState(str, Enum):
    IDLE = "idle"
    EXERCISING = "exercising"
    BREAK_TIMER = "break_timer"
    COMPLETED = "completed"

@dataclass(frozen=True)
class Exercise:
    name_en: str
    name_ar: str
    muscle_group: str
    sets: int
    rep_min: int
    rep_max: int
    duration_seconds: Optional[int] = None

DEFAULT_ROUTINE = [
    Exercise("Goblet Squat", "سكوات كوبلت", "Quads / Glutes", 4, 12, 15),
    Exercise("Dumbbell Floor Press", "ضغط دمبل على الأرض", "Chest / Triceps", 4, 12, 15),
    Exercise("Dumbbell Rows", "تجديف دمبل", "Back / Biceps", 4, 10, 12),
    Exercise("Romanian Deadlift", "رفعة رومانية", "Hamstrings / Lower Back", 3, 12, 12),
    Exercise("Dumbbell Shoulder Press", "ضغط كتف دمبل", "Shoulders", 3, 10, 12),
    Exercise("Dumbbell Bicep Curls", "بايسبس دمبل", "Arms", 3, 12, 15),
    Exercise("Plank", "بلانك", "Core", 3, 45, 45, duration_seconds=45),
]
ARABIC_NUMBERS = {0:"صفر",1:"واحد",2:"اتنين",3:"تلاتة",4:"اربعة",5:"خمسة",6:"ستة",7:"سبعة",8:"تمانية",9:"تسعة",10:"عشرة",11:"حداشر",12:"اتناشر",13:"تلاتاشر",14:"اربعتاشر",15:"خمستاشر",16:"ستاشر",17:"سبعتاشر",18:"تمانتاشر",19:"تسعتاشر",20:"عشرين"}

@dataclass
class WorkoutSnapshot:
    state: WorkoutState
    exercise_index: int
    exercise: Exercise
    set_number: int
    total_sets: int
    current_reps: int
    target_text: str
    break_remaining: int = 0
    message: str = ""
    completed: bool = False

@dataclass
class WorkoutStateMachine:
    routine: list[Exercise] = field(default_factory=lambda: list(DEFAULT_ROUTINE))
    rest_seconds: int = 75
    on_update: Optional[Callable[[WorkoutSnapshot], None]] = None
    on_speech: Optional[Callable[[str], None]] = None
    state: WorkoutState = WorkoutState.IDLE
    exercise_index: int = 0
    set_number: int = 1
    current_reps: int = 0
    last_rep_at: float = 0.0
    cooldown_seconds: float = 1.2
    break_remaining: int = 0

    def __post_init__(self):
        self._timer_stop = threading.Event(); self._timer_thread = None; self._lock = threading.RLock()
    @property
    def exercise(self): return self.routine[self.exercise_index]
    def snapshot(self, message=""):
        e = self.exercise; target = f"{e.rep_min}-{e.rep_max} تكرار" if e.duration_seconds is None else f"{e.duration_seconds} ثانية"
        return WorkoutSnapshot(self.state,self.exercise_index,e,self.set_number,e.sets,self.current_reps,target,self.break_remaining,message,self.state==WorkoutState.COMPLETED)
    def _emit(self, message=""):
        if self.on_update: self.on_update(self.snapshot(message))
    def _say(self, text):
        if self.on_speech: self.on_speech(text)
    def start(self):
        with self._lock:
            self.state=WorkoutState.EXERCISING; self.exercise_index=0; self.set_number=1; self.current_reps=0; self.last_rep_at=0
            self._say(f"ابدأ {self.exercise.name_ar}. المجموعة الأولى"); self._emit("بدأ التمرين"); return self.snapshot("بدأ التمرين")
    def register_rep(self, now=None):
        with self._lock:
            if self.state != WorkoutState.EXERCISING: return False
            now=time.monotonic() if now is None else now
            if now-self.last_rep_at < self.cooldown_seconds: return False
            self.last_rep_at=now; self.current_reps+=1; self._say(ARABIC_NUMBERS.get(self.current_reps,str(self.current_reps))); self._emit(f"التكرار {self.current_reps}"); return True
    def finish_set(self):
        with self._lock:
            if self.state != WorkoutState.EXERCISING: return self.snapshot("لا يوجد تمرين نشط")
            message=f"انتهت المجموعة {self.set_number}"
            if self.set_number < self.exercise.sets:
                self.state=WorkoutState.BREAK_TIMER; self.break_remaining=self.rest_seconds; self._say(f"تمام. راحة {self.rest_seconds} ثانية"); self._emit(message); self._start_timer()
            elif self.exercise_index < len(self.routine)-1:
                self.exercise_index+=1; self.set_number=1; self.current_reps=0; self._say(f"التمرين التالي: {self.exercise.name_ar}"); self._emit(message)
            else:
                self.state=WorkoutState.COMPLETED; self._say("خلصت كل التمارين. أحسنت"); self._emit("اكتمل التمرين")
            return self.snapshot(message)
    def _start_timer(self):
        self._timer_stop.set(); self._timer_stop=threading.Event(); self._timer_thread=threading.Thread(target=self._countdown,daemon=True); self._timer_thread.start()
    def _countdown(self):
        while not self._timer_stop.wait(1):
            with self._lock:
                if self.state != WorkoutState.BREAK_TIMER: return
                self.break_remaining-=1; self._emit("وقت الراحة")
                if self.break_remaining <= 0:
                    self.state=WorkoutState.EXERCISING; self.set_number+=1; self.current_reps=0; self.last_rep_at=0; self._say(f"جاهز. المجموعة {self.set_number}"); self._emit("انتهت الراحة"); return
    def handle_command(self, text):
        normalized=" ".join(text.strip().lower().split())
        if not normalized: return None
        if normalized in {"بريك","خلصت","break","done","finished"}: return self.finish_set()
        if normalized in {"جاهز","ready","ابدأ","start"}:
            if self.state==WorkoutState.IDLE: return self.start()
            if self.state==WorkoutState.BREAK_TIMER:
                with self._lock:
                    self.break_remaining=0; self.state=WorkoutState.EXERCISING; self.set_number+=1; self.current_reps=0; self._say(f"جاهز. المجموعة {self.set_number}"); self._emit("بدأت المجموعة التالية"); return self.snapshot("بدأت المجموعة التالية")
        if normalized in {"عدة","عد","تم","rep","count"}: self.register_rep(); return self.snapshot("تكرار")
        number=self._parse_number(normalized)
        if number is not None and self.state==WorkoutState.EXERCISING and number>self.current_reps:
            with self._lock: self.current_reps=number; self.last_rep_at=time.monotonic(); self._say(ARABIC_NUMBERS.get(number,str(number))); self._emit(f"التكرار {number}"); return self.snapshot(f"التكرار {number}")
        return None
    @staticmethod
    def _parse_number(text):
        aliases={v:k for k,v in ARABIC_NUMBERS.items()}; aliases.update({"واحد وعشرين":21,"اتنين وعشرين":22,"تلاتة وعشرين":23,"اربعة وعشرين":24,"خمسة وعشرين":25})
        return aliases.get(text)
    def stop(self):
        self._timer_stop.set()
        with self._lock:
            if self.state != WorkoutState.COMPLETED: self.state=WorkoutState.IDLE
            self._emit("تم إيقاف التمرين")

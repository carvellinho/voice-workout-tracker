"""Kivy UI for Voice Workout Tracker."""
from __future__ import annotations
from pathlib import Path
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex
try:
    from android.runnable import run_on_ui_thread
    from jnius import autoclass
except Exception:
    def run_on_ui_thread(fn): return fn
    autoclass=None
from .audio_engine import AudioEngine
from .database import WorkoutDatabase
from .state_machine import WorkoutSnapshot, WorkoutState, WorkoutStateMachine
from .tts_engine import TTSEngine

class WorkoutScreen(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(orientation="vertical",padding=dp(20),spacing=dp(12),**kwargs); self.app=app
        self.title=Label(text="VOICE WORKOUT",font_size=dp(25),bold=True,color=get_color_from_hex("#78FF73"),size_hint_y=.12)
        self.exercise=Label(text="جاهز؟",font_size=dp(30),bold=True,color=(1,1,1,1),halign="center",size_hint_y=.16)
        self.counter=Label(text="0",font_size=dp(105),bold=True,color=get_color_from_hex("#D8FF3E"),halign="center",size_hint_y=.30)
        self.details=Label(text="اضغط ابدأ أو قل: ابدأ",font_size=dp(20),color=(.8,.9,.95,1),halign="center",size_hint_y=.18)
        self.status=Label(text="الصوت متوقف",font_size=dp(16),color=(.7,.75,.8,1),halign="center",size_hint_y=.10)
        for w in (self.title,self.exercise,self.counter,self.details,self.status): self.add_widget(w)
        buttons=BoxLayout(size_hint_y=.14,spacing=dp(10))
        for text,fn in (("ابدأ",self.start),("تكرار +1",self.rep),("خلصت المجموعة",self.finish),("إيقاف",self.stop)):
            b=Button(text=text,font_size=dp(16),background_color=get_color_from_hex("#243447")); b.bind(on_release=lambda _,f=fn:f()); buttons.add_widget(b)
        self.add_widget(buttons)
    def start(self): self.app.machine.start(); self.app.start_audio()
    def rep(self): self.app.machine.register_rep()
    def finish(self): self.app.machine.finish_set()
    def stop(self): self.app.machine.stop(); self.app.stop_audio()
    def render(self,s:WorkoutSnapshot):
        self.exercise.text=f"{s.exercise.name_en}\n{s.exercise.name_ar}"
        self.counter.text=str(s.current_reps)
        state={WorkoutState.IDLE:"متوقف",WorkoutState.EXERCISING:f"المجموعة {s.set_number} من {s.total_sets}",WorkoutState.BREAK_TIMER:f"راحة: {s.break_remaining} ثانية",WorkoutState.COMPLETED:"اكتمل التمرين"}[s.state]
        self.details.text=f"{state}\nالهدف الإرشادي: {s.target_text}"
        self.status.text=s.message or "استمع للأوامر: عدة، بريك، خلصت"

class VoiceWorkoutApp(App):
    title="Voice Workout Tracker"
    def build(self):
        Window.clearcolor=get_color_from_hex("#101820"); self.db=WorkoutDatabase(); self.tts=TTSEngine(); self.screen=WorkoutScreen(self)
        self.machine=WorkoutStateMachine(on_update=lambda s:Clock.schedule_once(lambda _:self.screen.render(s)),on_speech=self.tts.speak)
        model=Path(__file__).resolve().parent.parent/"model"; self.audio=AudioEngine(model,self.handle_voice,lambda m:Clock.schedule_once(lambda _:setattr(self.screen.status,"text",m)))
        self._keep_screen_on(True); return self.screen
    def handle_voice(self,text): Clock.schedule_once(lambda _:self.machine.handle_command(text))
    def start_audio(self): self.audio.start()
    def stop_audio(self): self.audio.stop()
    @run_on_ui_thread
    def _keep_screen_on(self,enabled):
        try:
            if autoclass:
                activity=autoclass("org.kivy.android.PythonActivity").mActivity; view=activity.getWindow()
                if enabled: view.addFlags(128)
                else: view.clearFlags(128)
        except Exception: pass
    def on_stop(self): self.stop_audio(); self.tts.stop(); self.machine.stop(); self._keep_screen_on(False)

if __name__ == "__main__": VoiceWorkoutApp().run()

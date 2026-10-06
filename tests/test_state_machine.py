import time
import unittest
from src.state_machine import WorkoutState, WorkoutStateMachine

class StateMachineTests(unittest.TestCase):
    def setUp(self): self.m=WorkoutStateMachine(rest_seconds=1)
    def test_start_and_open_ended_counting(self):
        self.m.start()
        self.assertEqual(self.m.state,WorkoutState.EXERCISING)
        for i in range(16):
            self.m.last_rep_at=0
            self.assertTrue(self.m.register_rep(now=time.monotonic()+2+i))
        self.assertEqual(self.m.current_reps,16)
        self.assertEqual(self.m.state,WorkoutState.EXERCISING)
    def test_cooldown_blocks_duplicate(self):
        self.m.start(); now=time.monotonic(); self.assertTrue(self.m.register_rep(now=now)); self.assertFalse(self.m.register_rep(now=now+1.19)); self.assertTrue(self.m.register_rep(now=now+1.21))
    def test_finish_requires_explicit_command_and_starts_break(self):
        self.m.start(); self.m.current_reps=15; self.m.handle_command("خلصت"); self.assertEqual(self.m.state,WorkoutState.BREAK_TIMER); self.assertEqual(self.m.break_remaining,1)
    def test_generic_increment_word(self):
        self.m.start(); self.m.handle_command("عدة"); self.assertEqual(self.m.current_reps,1)
    def test_number_command_never_decreases_count(self):
        self.m.start(); self.m.handle_command("عشرة"); self.assertEqual(self.m.current_reps,10); self.m.handle_command("خمسة"); self.assertEqual(self.m.current_reps,10)

if __name__ == "__main__": unittest.main()

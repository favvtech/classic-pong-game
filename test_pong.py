"""
Automated Test Suite for Classic Pong Game
Verifies game mechanics, sprite classes, physics, collisions, and state serialization.
Runs headlessly without requiring a physical monitor or audio hardware.
"""

import os
import sys
import tempfile
import unittest
import json

# Ensure headless environment before importing pygame
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

from pong import PongGame, Paddle, Ball, FIELD_TOP, FIELD_BOTTOM, SCREEN_WIDTH, SCREEN_HEIGHT


class TestPongGame(unittest.TestCase):

    def setUp(self):
        """Initialize a headless PongGame instance before each test."""
        self.game = PongGame(headless=True)

    def tearDown(self):
        """Clean up game resources."""
        pass

    def test_paddle_boundaries_and_movement(self):
        """Verify paddle moves vertically with velocity vectors and clamps to court boundaries."""
        paddle = Paddle(x=100, y=300, height=80, speed=10.0)

        # 1. Test upward movement
        paddle.up_pressed = True
        paddle.update()
        self.assertEqual(paddle.velocity_y, -10.0)
        self.assertAlmostEqual(paddle.pos_y, 290.0)

        # 2. Test clamping at FIELD_TOP
        paddle.pos_y = FIELD_TOP + 10  # Very close to top
        paddle.update()
        min_allowed_y = FIELD_TOP + paddle.height / 2.0
        self.assertGreaterEqual(paddle.pos_y, min_allowed_y)

        # 3. Test downward movement
        paddle.up_pressed = False
        paddle.down_pressed = True
        paddle.update()
        self.assertEqual(paddle.velocity_y, 10.0)

        # 4. Test clamping at FIELD_BOTTOM
        paddle.pos_y = FIELD_BOTTOM - 5
        paddle.update()
        max_allowed_y = FIELD_BOTTOM - paddle.height / 2.0
        self.assertLessEqual(paddle.pos_y, max_allowed_y)

        # 5. Test stopping when both or neither keys pressed
        paddle.up_pressed = True
        paddle.down_pressed = True
        paddle.update()
        self.assertEqual(paddle.velocity_y, 0.0)

    def test_ball_wall_bounce(self):
        """Verify ball velocity vectors reflect upon hitting top and bottom walls."""
        ball = Ball(x=400, y=FIELD_TOP + 10, size=14, base_speed=5.0)
        ball.velocity_x = 5.0
        ball.velocity_y = -5.0  # Moving up toward top wall

        # Step frame: should bounce off top wall
        result = ball.update()
        self.assertEqual(result, 0)
        self.assertGreater(ball.velocity_y, 0, "Ball should reflect downwards off top wall")

        # Position near bottom wall moving downward
        ball.pos_y = FIELD_BOTTOM - 2
        ball.velocity_y = 6.0
        result = ball.update()
        self.assertEqual(result, 0)
        self.assertLess(ball.velocity_y, 0, "Ball should reflect upwards off bottom wall")

    def test_ball_paddle_collision_deflection(self):
        """Verify ball reflects off paddle with deflection angle and speed escalation."""
        paddle = Paddle(x=50, y=300, width=20, height=100)
        ball = Ball(x=55, y=300, size=14, base_speed=6.0)
        ball.velocity_x = -6.0
        ball.velocity_y = 0.0

        # Collision with left paddle
        initial_speed = ball.speed
        collided = ball.handle_paddle_collision(paddle, is_left_paddle=True)
        self.assertTrue(collided, "Ball should detect collision with paddle")
        self.assertGreater(ball.velocity_x, 0, "Ball should reverse horizontal direction to the right")
        self.assertGreater(ball.speed, initial_speed, "Ball speed should escalate on paddle bounce")

    def test_scoring_mechanism(self):
        """Verify score increases and ball resets when exiting bounds."""
        self.game.p1_score = 0
        self.game.p2_score = 0

        # Place ball exiting right boundary (P1 scores)
        self.game.ball.pos_x = SCREEN_WIDTH + 50
        self.game.ball.velocity_x = 5.0
        self.game.ball.velocity_y = 0.0

        self.game.update()
        self.assertEqual(self.game.p1_score, 1, "Player 1 score should increment when ball passes right edge")
        self.assertEqual(self.game.p2_score, 0)

        # Place ball exiting left boundary (P2 scores)
        self.game.ball.pos_x = -50
        self.game.ball.velocity_x = -5.0
        self.game.update()
        self.assertEqual(self.game.p2_score, 1, "Player 2 score should increment when ball passes left edge")

    def test_state_serialization_save_and_load(self):
        """
        Verify the save and load functionality:
        Serializes current match state (scores, paddle positions, ball coordinates/velocities)
        to JSON and correctly restores every attribute.
        """
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Set custom distinct game state
            self.game.p1_score = 7
            self.game.p2_score = 4
            self.game.paused = False
            self.game.paddle_left.pos_y = 185.5
            self.game.paddle_left.velocity_y = -7.0
            self.game.paddle_right.pos_y = 420.0
            self.game.paddle_right.velocity_y = 7.0
            self.game.ball.pos_x = 350.25
            self.game.ball.pos_y = 280.75
            self.game.ball.velocity_x = -8.2
            self.game.ball.velocity_y = 3.4
            self.game.ball.speed = 9.1

            # Save state
            success, msg = self.game.save_game(tmp_path)
            self.assertTrue(success, f"Save game should succeed: {msg}")
            self.assertTrue(os.path.exists(tmp_path), "Save file should exist on disk")

            # Verify raw JSON format
            with open(tmp_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["p1_score"], 7)
            self.assertEqual(data["p2_score"], 4)
            self.assertIn("paddle_left", data)
            self.assertIn("paddle_right", data)
            self.assertIn("ball", data)

            # Mutate state on active game
            self.game.p1_score = 0
            self.game.p2_score = 0
            self.game.paddle_left.pos_y = 300.0
            self.game.paddle_right.pos_y = 300.0
            self.game.ball.pos_x = 0.0

            # Load state back
            load_success, load_msg = self.game.load_game(tmp_path)
            self.assertTrue(load_success, f"Load game should succeed: {load_msg}")

            # Validate restored state
            self.assertEqual(self.game.p1_score, 7)
            self.assertEqual(self.game.p2_score, 4)
            self.assertAlmostEqual(self.game.paddle_left.pos_y, 185.5, places=2)
            self.assertAlmostEqual(self.game.paddle_right.pos_y, 420.0, places=2)
            self.assertAlmostEqual(self.game.ball.pos_x, 350.25, places=2)
            self.assertAlmostEqual(self.game.ball.pos_y, 280.75, places=2)
            self.assertAlmostEqual(self.game.ball.velocity_x, -8.2, places=2)
            self.assertAlmostEqual(self.game.ball.velocity_y, 3.4, places=2)
            self.assertAlmostEqual(self.game.ball.speed, 9.1, places=2)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_load_nonexistent_file(self):
        """Verify load handles missing files cleanly without crashing."""
        success, msg = self.game.load_game("non_existent_file_12345.json")
        self.assertFalse(success)
        self.assertIn("not found", msg)

    def test_persistence_across_relaunch(self):
        """
        Verify that saving, quitting (closing the game), and relaunching a fresh instance
        allows reloading the exact saved match state from disk.
        """
        save_path = "test_relaunch_save.json"
        try:
            # Session 1: Play and Save
            session1 = PongGame(headless=True, save_file=save_path)
            session1.p1_score = 9
            session1.p2_score = 6
            session1.paddle_left.pos_y = 220.0
            session1.paddle_right.pos_y = 380.0
            session1.ball.pos_x = 425.0
            session1.ball.pos_y = 295.0
            session1.ball.velocity_x = 8.5
            session1.ball.velocity_y = -3.2
            success, _ = session1.save_game(save_path)
            self.assertTrue(success)

            # Session 1 closes/terminates (session1 object destroyed)
            del session1

            # Session 2: Fresh launch
            session2 = PongGame(headless=True, save_file=save_path)
            # Starts as fresh match by default
            self.assertEqual(session2.p1_score, 0)
            self.assertEqual(session2.p2_score, 0)

            # Player presses Load key
            load_success, _ = session2.load_game(save_path)
            self.assertTrue(load_success)

            # Verify all state is accurately restored in Session 2
            self.assertEqual(session2.p1_score, 9)
            self.assertEqual(session2.p2_score, 6)
            self.assertAlmostEqual(session2.paddle_left.pos_y, 220.0, places=2)
            self.assertAlmostEqual(session2.paddle_right.pos_y, 380.0, places=2)
            self.assertAlmostEqual(session2.ball.pos_x, 425.0, places=2)
            self.assertAlmostEqual(session2.ball.pos_y, 295.0, places=2)
            self.assertAlmostEqual(session2.ball.velocity_x, 8.5, places=2)
            self.assertAlmostEqual(session2.ball.velocity_y, -3.2, places=2)

        finally:
            if os.path.exists(save_path):
                os.remove(save_path)


if __name__ == "__main__":
    unittest.main()

"""
Classic Pong Game - CSE310 Applied Programming
Built with Python and Pygame (pygame-ce).

Features:
- Window & graphics rendering with retro aesthetic and center dashed line.
- Sprite classes for Paddle and Ball with continuous velocity vectors.
- Event handlers for Player 1 (W/S) and Player 2 (UP/DOWN) vertical movement.
- Full physics: paddle deflection angles, wall bouncing, speed escalation.
- Save and Load functionality: serializes full game state (scores, paddle
  positions/velocities, ball coordinates/velocity) into a JSON file.
- On-screen HUD, pause/resume, reset, and toast notification system.
- Synthesized 8-bit sound effects (no external audio files required).
- Headless testing support for automated test suites.
"""

import sys
import os
import io
import math
import wave
import struct
import json
import argparse
from typing import Optional, Tuple, Dict, Any

import pygame

# -----------------------------------------------------------------------------
# CONSTANTS & CONFIGURATION
# -----------------------------------------------------------------------------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

FIELD_TOP = 70
FIELD_BOTTOM = 540
FIELD_LEFT = 20
FIELD_RIGHT = 780

COLOR_BG = (12, 14, 20)
COLOR_WHITE = (245, 245, 250)
COLOR_GRAY = (110, 115, 130)
COLOR_LIGHT_GRAY = (175, 180, 195)
COLOR_NET = (70, 75, 90)
COLOR_SUCCESS = (60, 210, 120)
COLOR_ERROR = (240, 80, 80)
COLOR_ACCENT = (255, 200, 60)
COLOR_P1 = (80, 170, 255)
COLOR_P2 = (255, 120, 100)

DEFAULT_SAVE_FILE = "pong_save.json"
WINNING_SCORE = 11


# -----------------------------------------------------------------------------
# RETRO SOUND GENERATOR (Built-in Audio Synthesis)
# -----------------------------------------------------------------------------
class SoundEffects:
    """Generates procedural 8-bit sound effects using the standard library wave module."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.hit_paddle: Optional[pygame.mixer.Sound] = None
        self.hit_wall: Optional[pygame.mixer.Sound] = None
        self.score_point: Optional[pygame.mixer.Sound] = None

        if not self.enabled:
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self._synthesize_sounds()
        except Exception:
            # Audio device unavailable or disabled
            self.enabled = False

    def _generate_tone(self, frequency: float, duration: float, volume: float = 0.25) -> Optional[pygame.mixer.Sound]:
        """Generates a square-wave 8-bit style beep in-memory."""
        sample_rate = 22050
        num_samples = int(sample_rate * duration)
        buf = io.BytesIO()

        with wave.open(buf, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)

            frames = bytearray()
            period = sample_rate / max(1.0, frequency)
            max_amp = int(32767 * volume)

            for i in range(num_samples):
                # Square wave with slight exponential decay for pleasant punch
                decay = 1.0 - (i / num_samples) * 0.4
                val = max_amp * decay if (i % period) < (period / 2) else -max_amp * decay
                frames.extend(struct.pack('<h', int(val)))

            wav_file.writeframes(frames)

        buf.seek(0)
        try:
            return pygame.mixer.Sound(buf)
        except Exception:
            return None

    def _synthesize_sounds(self):
        # Paddle hit: crisp high-mid tone (480Hz, 40ms)
        self.hit_paddle = self._generate_tone(480.0, 0.045, volume=0.22)
        # Wall bounce: slightly lower tone (260Hz, 35ms)
        self.hit_wall = self._generate_tone(260.0, 0.035, volume=0.18)
        # Score point: fanfare low-frequency drop (180Hz, 120ms)
        self.score_point = self._generate_tone(180.0, 0.12, volume=0.28)

    def play_paddle(self):
        if self.enabled and self.hit_paddle:
            self.hit_paddle.play()

    def play_wall(self):
        if self.enabled and self.hit_wall:
            self.hit_wall.play()

    def play_score(self):
        if self.enabled and self.score_point:
            self.score_point.play()


# -----------------------------------------------------------------------------
# SPRITE CLASSES
# -----------------------------------------------------------------------------
class Paddle(pygame.sprite.Sprite):
    """
    Paddle sprite controlled vertically by user input.
    Maintains floating-point position and velocity vectors.
    """

    def __init__(self, x: float, y: float, width: int = 14, height: int = 90,
                 speed: float = 7.0, color: Tuple[int, int, int] = COLOR_WHITE):
        super().__init__()
        self.width = width
        self.height = height
        self.speed = speed
        self.color = color

        self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.rect(self.image, self.color, (0, 0, self.width, self.height), border_radius=4)
        self.rect = self.image.get_rect()

        # Floating-point coordinates and velocity
        self.pos_x = float(x)
        self.pos_y = float(y)
        self.velocity_y = 0.0

        # Input state tracking
        self.up_pressed = False
        self.down_pressed = False

        self._sync_rect()

    def _sync_rect(self):
        self.rect.centerx = round(self.pos_x)
        self.rect.centery = round(self.pos_y)

    def update(self):
        """Update paddle position based on velocity vector and enforce boundary limits."""
        # Calculate velocity based on currently active keys
        if self.up_pressed and not self.down_pressed:
            self.velocity_y = -self.speed
        elif self.down_pressed and not self.up_pressed:
            self.velocity_y = self.speed
        else:
            self.velocity_y = 0.0

        self.pos_y += self.velocity_y

        # Clamp inside field boundaries
        min_y = FIELD_TOP + self.height / 2
        max_y = FIELD_BOTTOM - self.height / 2
        if self.pos_y < min_y:
            self.pos_y = min_y
            self.velocity_y = 0.0
        elif self.pos_y > max_y:
            self.pos_y = max_y
            self.velocity_y = 0.0

        self._sync_rect()

    def reset_position(self, y: float):
        self.pos_y = float(y)
        self.velocity_y = 0.0
        self.up_pressed = False
        self.down_pressed = False
        self._sync_rect()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize paddle state to dictionary."""
        return {
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
            "velocity_y": self.velocity_y,
            "up_pressed": self.up_pressed,
            "down_pressed": self.down_pressed
        }

    def from_dict(self, data: Dict[str, Any]):
        """Deserialize paddle state from dictionary."""
        self.pos_x = float(data.get("pos_x", self.pos_x))
        self.pos_y = float(data.get("pos_y", self.pos_y))
        self.velocity_y = float(data.get("velocity_y", 0.0))
        self.up_pressed = bool(data.get("up_pressed", False))
        self.down_pressed = bool(data.get("down_pressed", False))
        self._sync_rect()


class Ball(pygame.sprite.Sprite):
    """
    Ball sprite moving with 2D velocity vectors (velocity_x, velocity_y).
    Handles bounce physics, angle deflection off paddles, and speed scaling.
    """

    def __init__(self, x: float, y: float, size: int = 14,
                 base_speed: float = 6.0, max_speed: float = 14.0):
        super().__init__()
        self.size = size
        self.base_speed = base_speed
        self.max_speed = max_speed
        self.speed = base_speed

        self.image = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.rect(self.image, COLOR_WHITE, (0, 0, self.size, self.size), border_radius=3)
        self.rect = self.image.get_rect()

        self.pos_x = float(x)
        self.pos_y = float(y)
        self.velocity_x = 0.0
        self.velocity_y = 0.0

        self._sync_rect()

    def _sync_rect(self):
        self.rect.centerx = round(self.pos_x)
        self.rect.centery = round(self.pos_y)

    def serve(self, direction_x: int = 1, angle_deg: float = 15.0):
        """Serve the ball from center towards direction_x (1=Right, -1=Left)."""
        self.pos_x = SCREEN_WIDTH / 2.0
        self.pos_y = (FIELD_TOP + FIELD_BOTTOM) / 2.0
        self.speed = self.base_speed

        angle_rad = math.radians(angle_deg)
        self.velocity_x = direction_x * self.speed * math.cos(angle_rad)
        self.velocity_y = self.speed * math.sin(angle_rad)
        self._sync_rect()

    def update(self, sfx: Optional[SoundEffects] = None) -> int:
        """
        Updates position using velocity vectors and checks top/bottom wall collisions.
        Returns:
            0 if within bounds
            1 if Player 1 was scored on (ball passed left edge)
            2 if Player 2 was scored on (ball passed right edge)
        """
        self.pos_x += self.velocity_x
        self.pos_y += self.velocity_y

        half_size = self.size / 2.0

        # Top wall bounce
        if self.pos_y - half_size <= FIELD_TOP:
            self.pos_y = FIELD_TOP + half_size
            self.velocity_y = abs(self.velocity_y)
            if sfx:
                sfx.play_wall()

        # Bottom wall bounce
        elif self.pos_y + half_size >= FIELD_BOTTOM:
            self.pos_y = FIELD_BOTTOM - half_size
            self.velocity_y = -abs(self.velocity_y)
            if sfx:
                sfx.play_wall()

        self._sync_rect()

        # Check scoring
        if self.pos_x + half_size < 0:
            return 2  # Player 2 scores (ball exited left)
        elif self.pos_x - half_size > SCREEN_WIDTH:
            return 1  # Player 1 scores (ball exited right)

        return 0

    def handle_paddle_collision(self, paddle: Paddle, is_left_paddle: bool, sfx: Optional[SoundEffects] = None) -> bool:
        """
        Calculates collision and angle deflection against a paddle.
        Returns True if a bounce occurred.
        """
        if not self.rect.colliderect(paddle.rect):
            return False

        # Ensure collision is coming from the correct direction to prevent sticking
        if is_left_paddle and self.velocity_x > 0:
            return False
        if not is_left_paddle and self.velocity_x < 0:
            return False

        # Calculate relative impact point from -1.0 (top edge) to +1.0 (bottom edge)
        offset = (self.pos_y - paddle.pos_y) / (paddle.height / 2.0)
        offset = max(-1.0, min(1.0, offset))

        # Max deflection angle: 50 degrees
        max_bounce_angle = math.radians(50.0)
        bounce_angle = offset * max_bounce_angle

        # Increase speed slightly on each paddle hit for gameplay excitement
        self.speed = min(self.max_speed, self.speed + 0.4)

        direction = 1 if is_left_paddle else -1
        self.velocity_x = direction * self.speed * math.cos(bounce_angle)
        self.velocity_y = self.speed * math.sin(bounce_angle)

        # Reposition ball just outside paddle to prevent multi-frame clipping
        half_size = self.size / 2.0
        if is_left_paddle:
            self.pos_x = paddle.rect.right + half_size
        else:
            self.pos_x = paddle.rect.left - half_size

        self._sync_rect()

        if sfx:
            sfx.play_paddle()

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize ball state to dictionary."""
        return {
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
            "velocity_x": self.velocity_x,
            "velocity_y": self.velocity_y,
            "speed": self.speed
        }

    def from_dict(self, data: Dict[str, Any]):
        """Deserialize ball state from dictionary."""
        self.pos_x = float(data.get("pos_x", self.pos_x))
        self.pos_y = float(data.get("pos_y", self.pos_y))
        self.velocity_x = float(data.get("velocity_x", 0.0))
        self.velocity_y = float(data.get("velocity_y", 0.0))
        self.speed = float(data.get("speed", self.base_speed))
        self._sync_rect()


# -----------------------------------------------------------------------------
# MAIN GAME CLASS
# -----------------------------------------------------------------------------
class PongGame:
    """
    Main Pong Game application managing window, event loop, physics,
    state serialization, and rendering.
    """

    def __init__(self, headless: bool = False, winning_score: int = WINNING_SCORE,
                 save_file: str = DEFAULT_SAVE_FILE):
        self.headless = headless
        self.winning_score = winning_score
        self.save_file = save_file

        if self.headless:
            os.environ['SDL_VIDEODRIVER'] = 'dummy'
            os.environ['SDL_AUDIODRIVER'] = 'dummy'

        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Classic Pong - CSE310 Applied Programming")
        self.clock = pygame.time.Clock()

        # Initialize Fonts
        self.font_large = pygame.font.Font(None, 64)
        self.font_mid = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 22)

        # Audio synthesizer
        self.sfx = SoundEffects(enabled=not self.headless)

        # Game state variables
        self.running = False
        self.paused = False
        self.game_over = False
        self.winner = 0  # 1 = Player 1, 2 = Player 2

        self.p1_score = 0
        self.p2_score = 0

        # Toast notification system (text, color, expiration_ticks)
        self.toast_message = ""
        self.toast_color = COLOR_WHITE
        self.toast_timer = 0

        # Sprite setup
        self.all_sprites = pygame.sprite.Group()

        center_y = (FIELD_TOP + FIELD_BOTTOM) / 2.0
        self.paddle_left = Paddle(x=FIELD_LEFT + 25, y=center_y, color=COLOR_P1)
        self.paddle_right = Paddle(x=FIELD_RIGHT - 25, y=center_y, color=COLOR_P2)
        self.ball = Ball(x=SCREEN_WIDTH / 2.0, y=center_y)

        self.all_sprites.add(self.paddle_left)
        self.all_sprites.add(self.paddle_right)
        self.all_sprites.add(self.ball)

        # Start with fresh serve
        self.ball.serve(direction_x=1, angle_deg=20.0)

        # Notify if previous save file exists on disk
        if os.path.exists(self.save_file):
            self.show_toast("Saved game found! Press [F6] or [Ctrl+L] to Resume", COLOR_ACCENT, 240)

    def show_toast(self, message: str, color: Tuple[int, int, int] = COLOR_WHITE, duration_frames: int = 150):
        """Displays an on-screen toast notification."""
        self.toast_message = message
        self.toast_color = color
        self.toast_timer = duration_frames

    def reset_game(self):
        """Resets the match to a clean initial state."""
        self.p1_score = 0
        self.p2_score = 0
        self.paused = False
        self.game_over = False
        self.winner = 0

        center_y = (FIELD_TOP + FIELD_BOTTOM) / 2.0
        self.paddle_left.reset_position(center_y)
        self.paddle_right.reset_position(center_y)
        self.ball.serve(direction_x=1, angle_deg=15.0)

        self.show_toast("Match Reset to 0 - 0", COLOR_ACCENT)

    # -------------------------------------------------------------------------
    # SAVE & LOAD SERIALIZATION (Core Requirement)
    # -------------------------------------------------------------------------
    def save_game(self, filepath: Optional[str] = None) -> Tuple[bool, str]:
        """
        Serializes current match state (scores, paddle positions, ball coordinates/velocities)
        to a JSON file.
        """
        target_file = filepath or self.save_file
        state_data = {
            "version": "1.0",
            "p1_score": self.p1_score,
            "p2_score": self.p2_score,
            "paused": self.paused,
            "game_over": self.game_over,
            "winner": self.winner,
            "paddle_left": self.paddle_left.to_dict(),
            "paddle_right": self.paddle_right.to_dict(),
            "ball": self.ball.to_dict()
        }

        try:
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=4)
            msg = f"Game Saved Successfully to {os.path.basename(target_file)}"
            self.show_toast(msg, COLOR_SUCCESS)
            return True, msg
        except Exception as e:
            msg = f"Save Failed: {str(e)}"
            self.show_toast(msg, COLOR_ERROR)
            return False, msg

    def load_game(self, filepath: Optional[str] = None) -> Tuple[bool, str]:
        """
        Deserializes match state from a JSON file and restores all coordinates,
        velocities, and scores.
        """
        target_file = filepath or self.save_file
        if not os.path.exists(target_file):
            msg = f"Load Failed: '{os.path.basename(target_file)}' not found"
            self.show_toast(msg, COLOR_ERROR)
            return False, msg

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)

            # Restore Scores & Status
            self.p1_score = int(state_data.get("p1_score", 0))
            self.p2_score = int(state_data.get("p2_score", 0))
            self.paused = bool(state_data.get("paused", True))  # Resume safely
            self.game_over = bool(state_data.get("game_over", False))
            self.winner = int(state_data.get("winner", 0))

            # Restore Sprites
            if "paddle_left" in state_data:
                self.paddle_left.from_dict(state_data["paddle_left"])
            if "paddle_right" in state_data:
                self.paddle_right.from_dict(state_data["paddle_right"])
            if "ball" in state_data:
                self.ball.from_dict(state_data["ball"])

            msg = f"Game Loaded: {self.p1_score} - {self.p2_score}"
            self.show_toast(msg, COLOR_SUCCESS)
            return True, msg
        except Exception as e:
            msg = f"Corrupt Save File: {str(e)}"
            self.show_toast(msg, COLOR_ERROR)
            return False, msg

    # -------------------------------------------------------------------------
    # EVENT HANDLING
    # -------------------------------------------------------------------------
    def handle_events(self) -> bool:
        """
        Process keyboard events and window closing.
        Returns False if game should exit.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.KEYDOWN:
                # Quit on Escape
                if event.key == pygame.K_ESCAPE:
                    return False

                # Pause / Unpause
                elif event.key in (pygame.K_p, pygame.K_SPACE):
                    if not self.game_over:
                        self.paused = not self.paused
                        self.show_toast("PAUSED" if self.paused else "RESUMED", COLOR_LIGHT_GRAY, 60)

                # Reset match
                elif event.key == pygame.K_r:
                    self.reset_game()

                # Save Game: F5 or Ctrl+S
                elif event.key == pygame.K_F5 or (event.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL)):
                    self.save_game()

                # Load Game: F6 or F9 or Ctrl+L
                elif event.key in (pygame.K_F6, pygame.K_F9) or (event.key == pygame.K_l and (pygame.key.get_mods() & pygame.KMOD_CTRL)):
                    self.load_game()

                # Player 1 Movement (W / S) - ignore when Ctrl held
                if not (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    if event.key == pygame.K_w:
                        self.paddle_left.up_pressed = True
                    elif event.key == pygame.K_s:
                        self.paddle_left.down_pressed = True

                # Player 2 Movement (UP / DOWN)
                if event.key == pygame.K_UP:
                    self.paddle_right.up_pressed = True
                elif event.key == pygame.K_DOWN:
                    self.paddle_right.down_pressed = True

            elif event.type == pygame.KEYUP:
                # Player 1 Movement release
                if event.key == pygame.K_w:
                    self.paddle_left.up_pressed = False
                elif event.key == pygame.K_s:
                    self.paddle_left.down_pressed = False

                # Player 2 Movement release
                elif event.key == pygame.K_UP:
                    self.paddle_right.up_pressed = False
                elif event.key == pygame.K_DOWN:
                    self.paddle_right.down_pressed = False

        return True

    # -------------------------------------------------------------------------
    # PHYSICS & FRAME TICK UPDATE
    # -------------------------------------------------------------------------
    def update(self):
        """Advances physics by one frame update tick."""
        if self.toast_timer > 0:
            self.toast_timer -= 1

        if self.paused or self.game_over:
            return

        # 1. Update paddle positions via their velocity vectors
        self.paddle_left.update()
        self.paddle_right.update()

        # 2. Check collisions between ball and paddles
        self.ball.handle_paddle_collision(self.paddle_left, is_left_paddle=True, sfx=self.sfx)
        self.ball.handle_paddle_collision(self.paddle_right, is_left_paddle=False, sfx=self.sfx)

        # 3. Update ball position and check field scoring boundaries
        score_event = self.ball.update(sfx=self.sfx)

        if score_event == 1:
            # Player 1 scored!
            self.p1_score += 1
            self.sfx.play_score()
            if self.p1_score >= self.winning_score:
                self.game_over = True
                self.winner = 1
                self.show_toast("PLAYER 1 WINS THE MATCH!", COLOR_P1, 300)
            else:
                self.ball.serve(direction_x=-1, angle_deg=-15.0)  # Serve to Player 2
        elif score_event == 2:
            # Player 2 scored!
            self.p2_score += 1
            self.sfx.play_score()
            if self.p2_score >= self.winning_score:
                self.game_over = True
                self.winner = 2
                self.show_toast("PLAYER 2 WINS THE MATCH!", COLOR_P2, 300)
            else:
                self.ball.serve(direction_x=1, angle_deg=15.0)  # Serve to Player 1

    # -------------------------------------------------------------------------
    # DRAWING & RENDERING
    # -------------------------------------------------------------------------
    def draw(self):
        """Renders playing field, scores, sprites, HUD, and overlays."""
        self.screen.fill(COLOR_BG)

        # 1. Draw Court Borders
        pygame.draw.line(self.screen, COLOR_GRAY, (FIELD_LEFT, FIELD_TOP), (FIELD_RIGHT, FIELD_TOP), 3)
        pygame.draw.line(self.screen, COLOR_GRAY, (FIELD_LEFT, FIELD_BOTTOM), (FIELD_RIGHT, FIELD_BOTTOM), 3)

        # 2. Draw Retro Dashed Center Net
        net_x = SCREEN_WIDTH // 2
        segment_len = 12
        gap_len = 10
        cur_y = FIELD_TOP + 4
        while cur_y < FIELD_BOTTOM - 4:
            end_y = min(cur_y + segment_len, FIELD_BOTTOM - 4)
            pygame.draw.line(self.screen, COLOR_NET, (net_x, cur_y), (net_x, end_y), 3)
            cur_y += segment_len + gap_len

        # 3. Draw Scores
        p1_text = self.font_large.render(str(self.p1_score), True, COLOR_P1)
        p2_text = self.font_large.render(str(self.p2_score), True, COLOR_P2)
        self.screen.blit(p1_text, (net_x - 80 - p1_text.get_width() // 2, FIELD_TOP + 15))
        self.screen.blit(p2_text, (net_x + 80 - p2_text.get_width() // 2, FIELD_TOP + 15))

        # Player Labels
        lbl_p1 = self.font_small.render("PLAYER 1 (W/S)", True, COLOR_GRAY)
        lbl_p2 = self.font_small.render("PLAYER 2 (UP/DN)", True, COLOR_GRAY)
        self.screen.blit(lbl_p1, (FIELD_LEFT + 15, FIELD_TOP + 15))
        self.screen.blit(lbl_p2, (FIELD_RIGHT - 15 - lbl_p2.get_width(), FIELD_TOP + 15))

        # 4. Draw Sprites (Paddles and Ball)
        self.all_sprites.draw(self.screen)

        # 5. Top Header & Bottom Control Bar
        title_surf = self.font_mid.render("CLASSIC PONG", True, COLOR_WHITE)
        self.screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 18))

        controls_str = "[W/S] P1  |  [UP/DN] P2  |  [SPACE] Pause  |  [F5/Ctrl+S] Save  |  [F6/Ctrl+L] Load  |  [R] Reset"
        controls_surf = self.font_small.render(controls_str, True, COLOR_LIGHT_GRAY)
        self.screen.blit(controls_surf, (SCREEN_WIDTH // 2 - controls_surf.get_width() // 2, SCREEN_HEIGHT - 35))

        # 6. Toast Notification Banner
        if self.toast_timer > 0 and self.toast_message:
            toast_surf = self.font_mid.render(self.toast_message, True, self.toast_color)
            padding_x = 24
            padding_y = 10
            rect_w = toast_surf.get_width() + padding_x * 2
            rect_h = toast_surf.get_height() + padding_y * 2
            toast_rect = pygame.Rect(SCREEN_WIDTH // 2 - rect_w // 2, FIELD_BOTTOM - 60, rect_w, rect_h)

            # Translucent badge background
            badge_surf = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
            badge_surf.fill((20, 24, 35, 230))
            pygame.draw.rect(badge_surf, self.toast_color, (0, 0, rect_w, rect_h), width=2, border_radius=6)
            self.screen.blit(badge_surf, toast_rect.topleft)
            self.screen.blit(toast_surf, (toast_rect.x + padding_x, toast_rect.y + padding_y))

        # 7. Pause Overlay
        if self.paused and not self.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            self.screen.blit(overlay, (0, 0))

            paused_txt = self.font_large.render("PAUSED", True, COLOR_WHITE)
            resume_txt = self.font_mid.render("Press SPACE or P to Resume", True, COLOR_LIGHT_GRAY)
            self.screen.blit(paused_txt, (SCREEN_WIDTH // 2 - paused_txt.get_width() // 2, SCREEN_HEIGHT // 2 - 40))
            self.screen.blit(resume_txt, (SCREEN_WIDTH // 2 - resume_txt.get_width() // 2, SCREEN_HEIGHT // 2 + 30))

        # 8. Game Over Overlay
        if self.game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

            winner_name = f"PLAYER {self.winner} WINS!"
            win_color = COLOR_P1 if self.winner == 1 else COLOR_P2
            win_surf = self.font_large.render(winner_name, True, win_color)
            restart_surf = self.font_mid.render("Press 'R' to Start a New Match", True, COLOR_WHITE)

            self.screen.blit(win_surf, (SCREEN_WIDTH // 2 - win_surf.get_width() // 2, SCREEN_HEIGHT // 2 - 45))
            self.screen.blit(restart_surf, (SCREEN_WIDTH // 2 - restart_surf.get_width() // 2, SCREEN_HEIGHT // 2 + 25))

        pygame.display.flip()

    # -------------------------------------------------------------------------
    # MAIN LOOP
    # -------------------------------------------------------------------------
    def run(self):
        """Starts and maintains the 60 FPS game loop."""
        self.running = True
        while self.running:
            if not self.handle_events():
                self.running = False
                break

            self.update()

            if not self.headless:
                self.draw()

            self.clock.tick(FPS)

        pygame.quit()


# -----------------------------------------------------------------------------
# COMMAND-LINE ENTRY POINT
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Classic Pong Game (CSE310)")
    parser.add_argument("--headless", action="store_true", help="Run without creating a visible display window (for tests/CI)")
    parser.add_argument("--winning-score", type=int, default=WINNING_SCORE, help="Points needed to win the match (default: 11)")
    parser.add_argument("--save-file", type=str, default=DEFAULT_SAVE_FILE, help="Path to state serialization JSON file")
    args = parser.parse_args()

    game = PongGame(headless=args.headless, winning_score=args.winning_score, save_file=args.save_file)
    game.run()


if __name__ == "__main__":
    main()

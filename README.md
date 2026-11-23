# Overview

{Important!  Do not say in this section that this is college assignment.  Talk about what you are trying to accomplish as a software engineer to further your learning.}
As a software engineer, my goal with this project was to deepen my understanding of real-time game architecture, 2D vector kinematics, collision mathematics, and clean object-oriented design. Developing an interactive game from scratch provided practical experience in structuring deterministic 60 FPS game loops, managing decoupled sprite hierarchies, implementing state serialization systems, and generating procedural audio without relying on external media assets.

{Provide a description the game that you wrote. Describe how to play your game.}
I developed a modern recreation of the retro arcade classic Pong. The game features local two-player competitive gameplay where each player controls a vertical paddle on opposing ends of a bounded court. The objective is to return the bouncing ball across the court and past the opponent's paddle to score points.

How to Play:
* Player 1 (Left Paddle): Use `W` to move up and `S` to move down.
* Player 2 (Right Paddle): Use `Up Arrow` to move up and `Down Arrow` to move down.
* Aiming Mechanics: The ball deflects dynamically based on where it strikes the paddle—striking near paddle edges produces steep angles (up to $\pm 50^\circ$), while center hits produce direct horizontal returns. Ball speed progressively increases during extended rallies.
* Controls:
  * `Spacebar` / `P`: Pause and resume the match.
  * `F5` or `Ctrl + S`: Quick-save current game state to disk (`pong_save.json`).
  * `F6`, `F9`, or `Ctrl + L`: Quick-load and resume the saved match.
  * `R`: Reset the match back to 0 - 0.
  * `Escape`: Exit the game.
* Winning: The first player to reach 11 points wins the match.

{Describe your purpose for writing this software.}
The purpose of writing this software was to gain mastery over foundational software engineering principles applied to interactive graphical applications:
1. Kinematics & Physics: Implementing continuous floating-point velocity vectors ($\vec{v} = (v_x, v_y)$) and sub-pixel coordinate tracking to eliminate motion jitter.
2. Deterministic Collision Detection: Designing Axis-Aligned Bounding Box (AABB) collision algorithms paired with relative angle deflection and boundary penetration correction.
3. Robust State Persistence: Architecting a clean JSON-based serialization and deserialization engine that captures dynamic runtime states (scores, coordinates, velocities, and flags) to enable seamless persistence across game sessions.
4. Procedural Audio Generation: Generating retro 8-bit sound effects algorithmically in memory using mathematical wave synthesis (`wave` and `struct`), eliminating external asset dependencies.

{Provide a link to your YouTube demonstration.  It should be a 4-5 minute demo of the game being played and a walkthrough of the code.}

[Software Demo Video](http://youtube.link.goes.here)

# Development Environment

{Describe the tools that you used to develop the software}
* Operating System: Windows 11
* Integrated Development Environment (IDE):Visual Studio Code / Antigravity IDE
* Terminal & Shell: PowerShell 7 / Windows Terminal
* Version Control: Git

{Describe the programming language that you used and any libraries.}
* Programming Language: Python 3.14 (64-bit)
* Graphics & Windowing Framework: `pygame-ce` (Pygame Community Edition 2.5.8) for window management, surface rendering, sprite groups, and keyboard event queues.
* Python Standard Library:
  * `json`: For serializing and deserializing match states.
  * `math`: For trigonometric angle calculations and vector decomposition.
  * `wave` & `struct`: For procedural binary wave audio synthesis.
  * `io`: For handling in-memory byte streams (`io.BytesIO`) for audio playback.
  * `unittest`: For headless automated test suite execution.
  * `argparse`: For command-line argument configuration (e.g., `--headless`, `--winning-score`, `--save-file`).

# Useful Websites

{Make a list of websites that you found helpful in this project}
* [Pygame-ce Official Documentation](https://pyga.me/docs/)
* [Python 3 Standard Library Documentation](https://docs.python.org/3/)
* [Classic Pong Mechanics & History - Wikipedia](https://en.wikipedia.org/wiki/Pong)
* [Game Physics: 2D Elastic Collisions & Vectors](https://gamedevelopment.tutsplus.com/tutorials/how-to-create-a-custom-2d-physics-engine-oriented-rigid-bodies--gamedev-8032)

# Future Work

{Make a list of things that you need to fix, improve, and add in the future.}
* Implement an autonomous AI opponent with selectable difficulty levels (Easy, Medium, Hard) for solo play.
* Add dynamic power-ups that spawn intermittently on the field (e.g., paddle elongation, speed boosts, multi-ball).
* Enhance visual effects with retro CRT scanline shaders, particle bursts on paddle bounces, and screen shake on scoring.
* Introduce networked multiplayer via Python sockets or WebSockets to allow matches over local networks or the internet.

"""Estimate in-game FPS for a build.

The PC performance dataset has no FPS data, so this is NOT the ML model. It is
a transparent rule-based estimate:

  GPU-limited FPS = game's reference FPS at the resolution x GPU perf_index / 100
  CPU-limited FPS = game's CPU-limited FPS x CPU gaming_index / 100
  FPS             = smooth minimum of the two, adjusted for low RAM and
                    thermal throttling, then capped by the game's engine limit.

Reference values are approximate: the GPU-limited FPS an RTX 4090 would reach if
the CPU were not a limit, and the CPU-limited FPS of a Ryzen 7 9800X3D, at High
settings, native resolution, no upscaling or frame generation.
"""
import pandas as pd

RESOLUTIONS = ["1080p", "1440p", "4K"]

# name, genre, {resolution: GPU-limited FPS on the reference GPU}, CPU-limited FPS, engine cap
GAMES = [
    ("Cyberpunk 2077", "Open-world RPG", {"1080p": 210, "1440p": 145, "4K": 75}, 190, None),
    ("Black Myth: Wukong", "Action RPG", {"1080p": 135, "1440p": 105, "4K": 58}, 170, None),
    ("Red Dead Redemption 2", "Open-world action", {"1080p": 220, "1440p": 170, "4K": 95}, 180, None),
    ("Hogwarts Legacy", "Open-world RPG", {"1080p": 200, "1440p": 150, "4K": 80}, 140, None),
    ("Elden Ring", "Action RPG", {"1080p": 330, "1440p": 260, "4K": 150}, 150, 60),
    ("Call of Duty: Warzone", "Battle royale", {"1080p": 280, "1440p": 220, "4K": 125}, 260, None),
    ("Fortnite", "Battle royale", {"1080p": 330, "1440p": 250, "4K": 135}, 320, None),
    ("Apex Legends", "Battle royale", {"1080p": 500, "1440p": 400, "4K": 220}, 330, 300),
    ("GTA V", "Open-world action", {"1080p": 600, "1440p": 450, "4K": 230}, 185, 187),
    # Esports titles are light on the GPU: a flagship GPU is far from its limit
    ("Counter-Strike 2", "Competitive shooter", {"1080p": 1200, "1440p": 950, "4K": 550}, 600, None),
    ("Valorant", "Competitive shooter", {"1080p": 2000, "1440p": 1700, "4K": 1200}, 850, None),
    ("Minecraft (Java)", "Sandbox", {"1080p": 1500, "1440p": 1300, "4K": 900}, 450, None),
]

# Sharpness of the CPU/GPU "soft minimum": higher = closer to a hard min()
SOFT_MIN_POWER = 4


def _ram_factor(ram_gb: float) -> float:
    if ram_gb < 8:
        return 0.6
    if ram_gb < 16:
        return 0.85
    return 1.0


def _thermal_factor(temp_c: float) -> float:
    if temp_c >= 88:
        return 0.93
    if temp_c >= 80:
        return 0.97
    return 1.0


def gpu_index(cpu: dict, gpu: dict) -> float:
    """Graphics performance on the GPU scale; falls back to integrated graphics."""
    return gpu["perf_index"] if gpu["perf_index"] > 0 else cpu["igpu_index"]


def estimate_fps(cpu, gpu, ram_gb, temp_c, game, resolution) -> float:
    _, _, gpu_ref, cpu_ref, cap = game
    gpu_fps = gpu_ref[resolution] * gpu_index(cpu, gpu) / 100
    cpu_fps = cpu_ref * cpu["gaming_index"] / 100
    if gpu_fps <= 0 or cpu_fps <= 0:
        return 0.0
    fps = (gpu_fps ** -SOFT_MIN_POWER + cpu_fps ** -SOFT_MIN_POWER) ** (-1 / SOFT_MIN_POWER)
    fps *= _ram_factor(ram_gb) * _thermal_factor(temp_c)
    if cap:
        fps = min(fps, cap)
    return round(fps)


def experience(fps: float) -> str:
    if fps >= 144:
        return "Excellent (144+)"
    if fps >= 60:
        return "Smooth (60+)"
    if fps >= 30:
        return "Playable (30-60)"
    return "Struggles (<30)"


def fps_table(cpu, gpu, ram_gb, temp_c) -> pd.DataFrame:
    """Estimated FPS for every game at every resolution."""
    rows = []
    for game in GAMES:
        row = {"Game": game[0], "Genre": game[1]}
        for res in RESOLUTIONS:
            row[res] = estimate_fps(cpu, gpu, ram_gb, temp_c, game, res)
        rows.append(row)
    return pd.DataFrame(rows)

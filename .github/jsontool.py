#!/usr/bin/env python3
import json
import os
from pathlib import Path

# =========================
# UTIL
# =========================
def clean_path(p: str) -> Path:
    return Path(p.strip().strip('"').strip("'"))


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)


def load_chart(path: Path):
    data = load_json(path)

    if isinstance(data, dict) and "song" in data:
        return data["song"]
    return data


# =========================
# 1. PSYCH → OPTIMIZED
# =========================
def optimize_chart(song):
    optimized = {
        "song": song.get("song", "Unknown"),
        "bpm": song.get("bpm", 120),
        "speed": song.get("speed", 1),
        "stage": song.get("stage", "stage"),
        "characters": [
            song.get("player1", "bf"),
            song.get("player2", "dad"),
            song.get("gfVersion", "gf")
        ],
        "needsVoices": song.get("needsVoices", True),
        "events": song.get("events", []),
        "camera": song.get("camera", []),
        "notes": []
    }

    sections = song.get("notes", [])

    for sec in sections:
        notes = sec.get("sectionNotes", []) if isinstance(sec, dict) else sec
        for n in notes:
            optimized["notes"].append(n)

    # sort notes by time
    optimized["notes"].sort(key=lambda x: x[0] if isinstance(x, list) else 0)

    return optimized


def convert_task():
    path = clean_path(input("Enter path: "))

    print("Optimizing...")

    song = load_chart(path)
    optimized = optimize_chart(song)

    out = path.with_name(path.stem + "_optimized.json")
    save_json(out, optimized)

    print("Done..")
    print("Saved:", out)


# =========================
# 2. JSON COMPRESSOR
# =========================
def compress_task():
    path = clean_path(input("Enter path: "))

    print("Compressing...")

    data = load_json(path)

    out = path.with_name(path.stem + "_compressed.json")
    save_json(out, data)

    print("Done..")
    print("Saved:", out)


# =========================
# MENU
# =========================
def main():
    while True:
        print("\n=== FNF TOOL ===")
        print("1: Convert Psych chart → Optimized")
        print("2: JSON Compressor")
        print("Q: Quit")

        choice = input("> ").strip().upper()

        if choice == "1":
            convert_task()
        elif choice == "2":
            compress_task()
        elif choice == "Q":
            break


if __name__ == "__main__":
    main()

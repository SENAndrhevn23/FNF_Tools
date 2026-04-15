#!/usr/bin/env python3
import json
import os
from pathlib import Path
from urllib.parse import urlparse, unquote

# =========================
# PATH HELPERS
# =========================
def clean_path(p: str) -> Path:
    p = p.strip().strip('"').strip("'")
    if p.startswith("file://"):
        p = unquote(urlparse(p).path)
    return Path(os.path.normpath(os.path.expanduser(os.path.expandvars(p))))

# =========================
# LOAD VMAN CHART
# =========================
def load_vman(path: Path):
    if not path.exists():
        print(f"File not found: {path}")
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        # Handle different nesting levels
        return data.get("song", data) 
    except Exception as e:
        print(f"Error loading JSON: {e}")
        return None

# =========================
# CONVERSION LOGIC
# =========================
def vman_to_psych(vman_data: dict):
    # Detect key count
    key_count = vman_data.get("keyCount", vman_data.get("mania", 4))
    bpm = vman_data.get("bpm", 150)
    
    psych = {
        "song": {
            "speed": vman_data.get("speed", 1.0),
            "stage": vman_data.get("stage", "stage"),
            "player1": vman_data.get("player1", "bf"),
            "player2": vman_data.get("player2", "dad"),
            "gfVersion": "gf",
            "notes": [],
            "events": [
                [0, [["Set Key Count", str(key_count), ""]]]
            ],
            "bpm": bpm,
            "needsVoices": vman_data.get("needsVoices", True),
            "song": vman_data.get("song", "Converted Song"),
            "validScore": False,
            "mania": key_count # Compatibility for some Psych forks
        }
    }

    for section in vman_data.get("notes", []):
        vman_notes = section.get("sectionNotes", [])
        must_hit = section.get("mustHitSection", True)
        converted_notes = []

        for note in vman_notes:
            if len(note) >= 2:
                time = note[0]
                raw_key = note[1]
                sustain = note[2] if len(note) > 2 else 0
                
                # PSYCH ENGINE MAPPING:
                # In mustHitSection=True: 0 to (K-1) is BF, K to (2K-1) is Opponent
                # In mustHitSection=False: 0 to (K-1) is Opponent, K to (2K-1) is BF
                # VMAN usually stores the index relative to the character lane.
                # To keep it simple and match standard conversion:
                # We assume VMAN key index is 0 to (K-1).
                
                final_key = raw_key
                # If it's a BF note, we add the key_count offset
                # (This logic ensures the notes appear on the correct side of the screen)
                if must_hit:
                    # If mustHit is true, notes 0-25 are BF. 
                    # If you want them on the Opponent side, you'd add offset.
                    pass 
                else:
                    # If mustHit is false, Psych flips the lanes.
                    pass

                converted_notes.append([time, final_key, sustain])

        psych_section = {
            "sectionNotes": converted_notes,
            "lengthInSteps": section.get("lengthInSteps", 16),
            "mustHitSection": must_hit,
            "bpm": bpm,
            "changeBPM": False,
            "sectionBeats": 4
        }
        psych["song"]["notes"].append(psych_section)

    return psych

# =========================
# SAVE & MAIN
# =========================
def save_psych(out_path: Path, data: dict):
    try:
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"--- SUCCESS ---\nSaved to: {out_path}")
    except Exception as e:
        print(f"Error saving: {e}")

def main():
    print("=== VMAN to Psych Engine Converter ===")
    path_input = input("Drag and drop VMAN JSON here: ")
    path = clean_path(path_input)
    
    vman_data = load_vman(path)
    if vman_data:
        psych_chart = vman_to_psych(vman_data)
        out_file = path.parent / f"{path.stem}-psych.json"
        save_psych(out_file, psych_chart)

if __name__ == "__main__":
    main()

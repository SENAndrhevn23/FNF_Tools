import json
import os
import copy
import time
from pathlib import Path
import mido

# ======================================
# CONFIG
# ======================================
ROOT_FOLDER = Path(r"C:\Users\andre\Documents\CHARTS")
ROOT_FOLDER.mkdir(exist_ok=True)

# ======================================
# COLORS (for console output)
# ======================================
class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    RESET = "\033[0m"

def c(text, color=Color.RESET):
    return f"{color}{text}{Color.RESET}"

# ======================================
# PATH UTILITIES
# ======================================
def clean_path(path: str) -> str:
    """Removes quotes and whitespace"""
    return path.strip().strip('"').strip("'")

def make_folder(name: str) -> Path:
    path = ROOT_FOLDER / name
    path.mkdir(exist_ok=True)
    return path

def compress_json(data):
    return json.dumps(data, separators=(",", ":"))

# ======================================
# FIX NOTE SIDES (Script 2 feature)
# ======================================
def fix_note_side(note):
    """Ensures player notes go on lanes 4-7, opponent on 0-3"""
    if len(note) < 4:
        return note

    time_, lane, length, mp = note

    # Normalize mustPress
    if isinstance(mp, bool):
        mp = 1 if mp else 0
    else:
        try:
            mp = int(mp)
        except:
            mp = 0

    if mp == 1:  # Player
        lane = (lane % 4) + 4
    else:        # Opponent
        lane = lane % 4

    return [time_, lane, length, mp]

# ======================================
# TIMER DECORATOR
# ======================================
def timer(func):
    def wrapper(*a, **k):
        start = time.time()
        print(c(f"\nStarted: {func.__name__}", Color.MAGENTA))
        result = func(*a, **k)
        end = time.time()
        print(c(f"Completed in {end - start:.2f}s", Color.GREEN))
        return result
    return wrapper

# ======================================
# FEATURES
# ======================================

@timer
def merge_charts():
    folder = make_folder("MERGED")
    files = []

    print("Enter chart paths one by one. Type 'stop' when done.")
    while True:
        p = clean_path(input("> "))
        if p.lower() == "stop":
            break
        fp = Path(p)
        if fp.exists():
            files.append(fp)
        else:
            print(c("File not found!", Color.RED))

    if not files:
        print(c("No files to merge!", Color.RED))
        return

    # Load first file
    with files[0].open("r", encoding="utf-8") as f:
        merged = json.load(f)

    # Merge others
    for fpath in files[1:]:
        with fpath.open("r", encoding="utf-8") as f:
            chart = json.load(f)

        for sec in chart["song"]["notes"]:
            new_sec = {"sectionNotes": []}
            for note in sec.get("sectionNotes", []):
                new_sec["sectionNotes"].append(fix_note_side(note))
            merged["song"]["notes"].append(new_sec)

    out_file = folder / "merged.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    print(c("Merged successfully!", Color.GREEN))
    print(f"Saved: {out_file}")

@timer
def split_chart():
    path = Path(clean_path(input("Path to chart: ")))
    if not path.exists():
        print(c("File not found!", Color.RED))
        return

    try:
        parts = int(input("Number of splits: "))
        if parts < 2:
            raise ValueError
    except ValueError:
        print(c("Invalid number!", Color.RED))
        return

    with path.open("r", encoding="utf-8") as f:
        base = json.load(f)

    sections = base["song"]["notes"]
    total = len(sections)
    chunk = total // parts

    folder = make_folder("SPLIT")

    i = 0
    start = 0
    while i < parts:
        end = start + chunk
        if i == parts - 1:
            end = total

        new_chart = copy.deepcopy(base)
        new_chart["song"]["notes"] = sections[start:end]

        # Normalize lanes/mustPress
        for sec in new_chart["song"]["notes"]:
            sec["sectionNotes"] = [fix_note_side(n) for n in sec.get("sectionNotes", [])]

        out_file = folder / f"{path.stem}_part{i+1}.json"
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(new_chart, f, indent=2)

        print(f"Saved {out_file} ({end - start} sections)")
        start = end
        i += 1

@timer
def multiply_notes_streamed():
    path = Path(clean_path(input("Enter path to chart: ")))

    if not path.exists():
        print(c("File not found!", Color.RED))
        return

    try:
        multiplier = int(input("Multiplier (max 2,000,000,000): ").strip())
        if multiplier < 2:
            raise ValueError
    except ValueError:
        print(c("Invalid multiplier!", Color.RED))
        return

    folder = make_folder("MULTIPLIED")
    out_file = folder / f"{path.stem}_x{multiplier}.json"

    with path.open("r", encoding="utf-8") as f:
        base = json.load(f)

    with out_file.open("w", encoding="utf-8") as out:
        out.write('{"song":{')

        for k, v in base["song"].items():
            if k != "notes":
                out.write(f'"{k}":{json.dumps(v)},')

        out.write('"notes":[')

        first_section = True
        total_notes_in = 0
        total_notes_out = 0

        for section in base["song"]["notes"]:
            if not first_section:
                out.write(",")
            first_section = False

            out.write('{"sectionNotes":[')

            notes = section.get("sectionNotes", [])
            total_notes_in += len(notes)

            first_note = True
            for note in notes:
                fixed = fix_note_side(note)
                note_dump = json.dumps(fixed)

                for _ in range(multiplier):
                    if not first_note:
                        out.write(",")
                    out.write(note_dump)
                    first_note = False
                    total_notes_out += 1

            out.write("]}")

        out.write("]}")
        out.write("}")

    print(c("SUCCESS — Streamed multiplier finished!", Color.GREEN))
    print(f"Saved: {out_file}")
    print(c(f"Notes Before: {total_notes_in}", Color.YELLOW))
    print(c(f"Notes After:  {total_notes_out}", Color.YELLOW))

@timer
def compress_chart():
    path = Path(clean_path(input("Path to chart: ")))
    if not path.exists():
        print(c("File not found!", Color.RED))
        return

    folder = make_folder("COMPRESSED")

    with path.open("r", encoding="utf-8") as f:
        chart = json.load(f)

    # Fix all lanes/mustPress before compression
    for sec in chart["song"]["notes"]:
        sec["sectionNotes"] = [fix_note_side(n) for n in sec.get("sectionNotes", [])]

    out_file = folder / f"{path.stem}_compressed.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(chart, f, separators=(",", ":"))

    print(c("Compression complete!", Color.GREEN))
    print(f"Saved: {out_file}")

@timer
def chart_details():
    path = Path(clean_path(input("Enter path to chart: ")))
    if not path.exists():
        print(c("File not found!", Color.RED))
        return

    with path.open("r", encoding="utf-8") as f:
        chart = json.load(f)

    song = chart["song"]

    sections = song["notes"]
    total_sections = len(sections)
    total_notes = sum(len(sec["sectionNotes"]) for sec in sections)

    print(c("\n=== CHART DETAILS ===", Color.YELLOW))
    print(f"Song Name:     {song.get('song','')}")
    print(f"BPM:           {song.get('bpm','')}")
    print(f"Stage:         {song.get('stage','')}")
    print(f"Player1:       {song.get('player1','')}")
    print(f"Player2:       {song.get('player2','')}")
    print(f"NeedsVoices:   {song.get('needsVoices','')}")
    print(f"ArrowSkin:     {song.get('arrowSkin','')}")
    print()
    print(f"Sections:      {total_sections}")
    print(f"Total Notes:   {total_notes}")
    print("=======================")

@timer
def midi_to_fnf():
    midi_path = clean_path(input("Enter MIDI path: ").strip())
    if not os.path.exists(midi_path):
        print(f"❌ File not found: {midi_path}")
        return

    try:
        bpm = float(input("Enter BPM (example 120): ").strip())
    except ValueError:
        print("❌ Invalid BPM. Using default 120.")
        bpm = 120.0

    print("Converting to JSON...")
    mid = mido.MidiFile(midi_path)
    ticks_per_beat = mid.ticks_per_beat
    ms_per_tick = (60000 / bpm) / ticks_per_beat

    notes = []
    time_accum = 0
    for msg in mid:
        time_accum += msg.time * ms_per_tick
        if msg.type == "note_on" and msg.velocity > 0:
            lane = msg.note % 4
            notes.append({"time": round(time_accum, 2), "lane": lane, "sustain": 0})

    chart = {
        "song": {
            "song": os.path.splitext(os.path.basename(midi_path))[0],
            "bpm": bpm,
            "notes": [{"sectionNotes": notes, "sectionBPM": bpm}],
        }
    }

    folder_path = make_folder("MidiToFNF Folder")
    new_file = os.path.join(folder_path, f"{chart['song']['song']}_converted.json")

    with open(new_file, "w", encoding="utf-8") as f:
        json.dump(chart, f, indent=4)

    print("✅ Done. MIDI converted successfully.")
    print(f"Saved in {folder_path}")

# ======================================
# MAIN MENU LOOP
# ======================================
def menu():
    while True:
        print("\n===================================")
        print("FNF MULTITOOL — Streamlined Edition")
        print("===================================")
        print("1: Multiply Notes (Streamed, Fast)")
        print("2: Merge Charts")
        print("3: Split Chart")
        print("4: Ultra Compress JSON")
        print("5: Chart Details")
        print("6: MIDI to FNF Chart")
        print("Q: Quit")

        choice = input("\nSelect option: ").strip().upper()

        match choice:
            case "1": multiply_notes_streamed()
            case "2": merge_charts()
            case "3": split_chart()
            case "4": compress_chart()
            case "5": chart_details()
            case "6": midi_to_fnf()
            case "Q": break
            case _: print(c("Invalid choice!", Color.RED))

if __name__ == "__main__":
    print(c("⚡ FNF MULTITOOL — Streamlined Edition ⚡", Color.YELLOW))
    print(c("Note: Player/Opponent lanes fixed automatically.\n", Color.GREEN))
    menu()

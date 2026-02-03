import json
import copy
import time
import argparse
from pathlib import Path
import math
import sys

# =========================
# COLORS / LOGGING
# =========================
class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'

def c(text, color=Color.RESET):
    return f"{color}{text}{Color.RESET}"

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        print(c(f"\n▶ {func.__name__}", Color.MAGENTA))
        result = func(*args, **kwargs)
        print(c(f"✔ Done in {time.time() - start:.2f}s", Color.GREEN))
        return result
    return wrapper

# =========================
# PATHS / IO
# =========================
ROOT = Path.cwd() / "CHART_OUTPUT"
ROOT.mkdir(exist_ok=True)

def clean_path(p: str) -> Path:
    return Path(p.strip().strip('"').strip("'"))

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(c(f"JSON load failed: {e}", Color.RED))
        return None

def save_json(folder: str, name: str, data):
    out_dir = ROOT / folder
    out_dir.mkdir(exist_ok=True)
    out = out_dir / name
    out.write_text(json.dumps(data, indent=4))
    print(c(f"Saved → {out}", Color.GREEN))

# =========================
# VALIDATION
# =========================
def valid_chart(chart):
    try:
        return "song" in chart and "notes" in chart["song"]
    except Exception:
        return False

def last_note_time(chart):
    t = 0
    for sec in chart["song"]["notes"]:
        for n in sec.get("sectionNotes", []):
            t = max(t, n[0])
    return t

# =========================
# FEATURES
# =========================
@timer
def append_notes(path: Path):
    chart = load_json(path)
    if not chart or not valid_chart(chart):
        return

    pool = []
    for sec in chart["song"]["notes"]:
        pool.extend(copy.deepcopy(sec.get("sectionNotes", [])))

    added = 0
    for sec in chart["song"]["notes"]:
        if not sec.get("sectionNotes"):
            sec["sectionNotes"] = copy.deepcopy(pool)
            added += 1

    save_json("Append", f"{path.stem}_appended.json", chart)
    print(f"Sections filled: {added}")

@timer
def multiply_notes(path: Path, multiplier: int, offset=0):
    if multiplier < 2:
        print(c("Multiplier must be >= 2", Color.RED))
        return

    chart = load_json(path)
    if not chart or not valid_chart(chart):
        return

    for sec in chart["song"]["notes"]:
        original = sec.get("sectionNotes", [])
        new_notes = []

        for i in range(multiplier):
            for note in original:
                n = copy.deepcopy(note)
                if offset > 0:
                    n[0] += i * offset
                new_notes.append(n)

        sec["sectionNotes"] = new_notes

    save_json("Multiply", f"{path.stem}_x{multiplier}.json", chart)

@timer
def split_chart(path: Path, parts: int):
    if parts < 2:
        print(c("Split count must be >= 2", Color.RED))
        return

    chart = load_json(path)
    if not chart or not valid_chart(chart):
        return

    notes = chart["song"]["notes"]
    size = math.ceil(len(notes) / parts)

    for i in range(parts):
        chunk = notes[i * size:(i + 1) * size]
        if not chunk:
            continue

        new_chart = copy.deepcopy(chart)
        new_chart["song"]["notes"] = chunk
        save_json("Split", f"{path.stem}_part{i+1}.json", new_chart)

@timer
def merge_charts(paths):
    charts = []
    for p in paths:
        ch = load_json(clean_path(p))
        if ch and valid_chart(ch):
            charts.append(ch)

    if not charts:
        print(c("No valid charts to merge", Color.RED))
        return

    base = charts[0]
    base_time = last_note_time(base) + 100

    for ch in charts[1:]:
        for sec in ch["song"]["notes"]:
            for note in sec.get("sectionNotes", []):
                note[0] += base_time
        base["song"]["notes"].extend(copy.deepcopy(ch["song"]["notes"]))
        base_time = last_note_time(base) + 100

    save_json("Merged", "merged.json", base)

@timer
def compress_json(path: Path):
    chart = load_json(path)
    if not chart:
        return

    out = ROOT / "Compressed"
    out.mkdir(exist_ok=True)
    file = out / f"{path.stem}_compressed.json"
    file.write_text(json.dumps(chart, separators=(",", ":")))
    print(c("Compressed successfully", Color.GREEN))

# =========================
# CLI
# =========================
parser = argparse.ArgumentParser("FNF Multitask Tool (Safe)")
parser.add_argument("--action", help="0-4 or Q")
parser.add_argument("--file")
parser.add_argument("--multiply", type=int)
parser.add_argument("--offset", type=int, default=0)
parser.add_argument("--split", type=int)
parser.add_argument("--merge", nargs="*")
args = parser.parse_args()

# =========================
# MENU
# =========================
def menu():
    print("""
===============================
FNF MULTITASK TOOL (SAFE)
===============================
0 - Append notes
1 - Merge charts
2 - Split chart
3 - Multiply notes (SAFE)
4 - Compress JSON
Q - Quit
""")
    return input("Select: ").upper()

# =========================
# MAIN
# =========================
def main():
    if args.action:
        a = args.action.upper()
        if a == "0":
            append_notes(clean_path(args.file))
        elif a == "1":
            merge_charts(args.merge)
        elif a == "2":
            split_chart(clean_path(args.file), args.split)
        elif a == "3":
            multiply_notes(clean_path(args.file), args.multiply, args.offset)
        elif a == "4":
            compress_json(clean_path(args.file))
        return

    while True:
        c_ = menu()
        if c_ == "Q":
            sys.exit()
        elif c_ == "0":
            append_notes(clean_path(input("JSON: ")))
        elif c_ == "1":
            merge_charts(input("Charts: ").split())
        elif c_ == "2":
            split_chart(clean_path(input("JSON: ")), int(input("Parts: ")))
        elif c_ == "3":
            multiply_notes(
                clean_path(input("JSON: ")),
                int(input("Multiplier: ")),
                int(input("Time offset (ms, 0 ok): "))
            )
        elif c_ == "4":
            compress_json(clean_path(input("JSON: ")))

if __name__ == "__main__":
    print(c("FNF MULTITASK TOOL — SAFE BUILD", Color.YELLOW))
    main()

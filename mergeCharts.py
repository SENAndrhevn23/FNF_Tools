#!/usr/bin/env python3
import json, copy, math, os, shlex, gc
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import List

# =========================
# COLORS
# =========================
class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def c(text, color=Color.RESET):
    return f"{color}{text}{Color.RESET}"

# =========================
# HELPERS
# =========================
def clean_path(p: str) -> Path:
    p = p.strip().strip('"').strip("'")
    if p.startswith("file://"):
        p = unquote(urlparse(p).path)
    return Path(os.path.normpath(os.path.expanduser(os.path.expandvars(p))))

def load_chart(path: Path):
    if not path.exists():
        print(c(f"File not found: {path}", Color.RED))
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(c(f"JSON error: {e}", Color.RED))
        return None

def save_json(path: Path, data: dict, compress=False):
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as f:
        if compress:
            json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
        else:
            json.dump(data, f, indent=4, ensure_ascii=False)
    if path.exists():
        try: path.unlink()
        except: pass
    temp.rename(path)

def count_notes(chart):
    total = 0
    for sec in chart.get("notes", []):
        if isinstance(sec, dict):
            total += len(sec.get("sectionNotes", []))
        elif isinstance(sec, list):
            total += len(sec)
    return total

def get_notes(sec):
    if isinstance(sec, dict):
        return sec.get("sectionNotes", [])
    if isinstance(sec, list):
        return sec
    return []

# =========================
# MERGE
# =========================
def merge_task(paths: List[Path]):
    # expand folders into json files
    expanded = []

    for p in paths:
        if p.is_dir():
            expanded.extend(sorted(p.glob("*.json")))
        else:
            expanded.append(p)

    if not expanded:
        print(c("No files found.", Color.RED))
        return False

    charts = []
    for p in expanded:
        data = load_chart(p)
        if data:
            charts.append(data)

    if not charts:
        print(c("No valid charts.", Color.RED))
        return False

    base = copy.deepcopy(charts[0])
    max_sections = max(len(c.get("notes", [])) for c in charts)

    merged = []

    for i in range(max_sections):
        template = None
        notes = []

        for ch in charts:
            secs = ch.get("notes", [])
            if i >= len(secs):
                continue

            sec = secs[i]

            if template is None:
                template = copy.deepcopy(sec) if isinstance(sec, dict) else {"sectionNotes": []}

            for n in get_notes(sec):
                notes.append(copy.deepcopy(n))

        if template is None:
            template = {
                "gfSection": False,
                "altAnim": False,
                "sectionNotes": [],
                "bpm": base.get("bpm", 100),
                "sectionBeats": 4,
                "changeBPM": False,
                "mustHitSection": True
            }

        notes.sort(key=lambda x: x[0] if isinstance(x, list) else 0)
        template["sectionNotes"] = notes
        merged.append(template)

    base["notes"] = merged

    # merge events
    events = []
    for ch in charts:
        events.extend(ch.get("events", []))
    base["events"] = events

    out = expanded[0].parent / "merged_result.json"
    save_json(out, base)

    return True
# =========================
# MULTIPLY
# =========================
def multiply_task(path: Path, mult: int):
    chart = load_chart(path)
    if not chart: return

    secs = chart.get("notes", [])
    new_secs = []

    offset = float(input("Offset between layers (ms, 0 = overlap): ") or 0)

    for i in range(mult):
        for sec in secs:
            ns = copy.deepcopy(sec)
            for n in get_notes(ns):
                if isinstance(n, list) and len(n) > 0:
                    n[0] += i * offset
            new_secs.append(ns)

    chart["notes"] = new_secs

    out = path.parent / f"{path.stem}_x{mult}.json"
    save_json(out, chart)

    print(c("Multiply done!", Color.GREEN))

# =========================
# SPLIT
# =========================
def split_task(path: Path, parts: int):
    chart = load_chart(path)
    if not chart: return

    secs = chart.get("notes", [])
    chunk = math.ceil(len(secs)/parts)

    for i in range(parts):
        new_chart = copy.deepcopy(chart)
        new_chart["notes"] = secs[i*chunk:(i+1)*chunk]

        out = path.parent / f"{path.stem}_part{i+1}.json"
        save_json(out, new_chart)

    print(c("Split done!", Color.GREEN))

# =========================
# ADD NOTES
# =========================
def add_notes_task():
    path = clean_path(input("Path: "))
    chart = load_chart(path) if path.exists() else {"notes":[]}

    n = int(input("How many notes: "))
    name = input("Output name: ")

    if not chart.get("notes"):
        chart["notes"] = [{"sectionNotes": []}]

    for _ in range(n):
        chart["notes"][0]["sectionNotes"].append([0,0,0])

    out = path.parent / f"{name}.json"
    save_json(out, chart)

    print(c("Notes added!", Color.GREEN))

# =========================
# COMPRESSOR
# =========================
def compressor_task(path: Path):
    chart = load_chart(path)
    if not chart: return

    out = path.parent / f"{path.stem}_compressed.json"
    save_json(out, chart, compress=True)

    print(c("Compressed!", Color.GREEN))
    print(f"Before: {path.stat().st_size:,}")
    print(f"After : {out.stat().st_size:,}")

# =========================
# MENU
# =========================
def main():
    while True:
        print(c("\n[FNF MULTI-TOOL CLEAN]", Color.MAGENTA))
        print("1 - Multiply")
        print("2 - Merge")
        print("3 - Split")
        print("4 - Compressor")
        print("5 - Add Notes")
        print("Q - Quit")

        ch = input("Select: ").upper()

        try:
            if ch == "1":
                p = clean_path(input("Path: "))
                m = int(input("Multiplier: "))
                multiply_task(p, m)

            elif ch == "2":
                raw = input("Paths: ")
                merge_task([clean_path(x) for x in shlex.split(raw)])

            elif ch == "3":
                p = clean_path(input("Path: "))
                n = int(input("Parts: "))
                split_task(p, n)

            elif ch == "4":
                p = clean_path(input("Path: "))
                compressor_task(p)

            elif ch == "5":
                add_notes_task()

            elif ch == "Q":
                break

        except Exception as e:
            print(c(f"Error: {e}", Color.RED))

        gc.collect()

if __name__ == "__main__":
    main()

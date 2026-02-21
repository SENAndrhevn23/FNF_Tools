#!/usr/bin/env python3
import json, copy, time, math, sys, os, shlex
from pathlib import Path
from urllib.parse import urlparse, unquote
from functools import wraps
from typing import Union, List, Iterator

# =========================
# CONFIG & COLORS
# =========================
MAX_SIZE_MB = 1990 

class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'

def c(text: str, color: str = Color.RESET) -> str:
    return f"{color}{text}{Color.RESET}"

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        print(c(f"Done in {time.time() - start:.2f}s\n", Color.GREEN))
        return result
    return wrapper

# =========================
# PATH & IO HELPERS
# =========================
def clean_path(p: Union[str, Path, None]) -> Path:
    if p is None: return Path(".")
    p = str(p).strip().strip('"').strip("'")
    if p.startswith("file://"):
        p = unquote(urlparse(p).path)
    return Path(os.path.normpath(os.path.expanduser(os.path.expandvars(p))))

def load_json(path: Path):
    if not path.exists(): return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(c(f"Error loading JSON: {e}", Color.RED))
        return None

def calculate_loop_ms(chart: dict) -> float:
    """Calculates total duration in ms to offset repeated notes."""
    bpm = chart["song"].get("bpm", 100)
    ms_per_beat = 60000 / bpm
    total_ms = 0
    for sec in chart["song"]["notes"]:
        beats = sec.get("sectionBeats", 4)
        total_ms += beats * ms_per_beat
    return total_ms

# =========================
# THE FIX: STREAMING & METADATA
# =========================
def _write_valid_fnf_json(out_path: Path, metadata: dict, sections_iter: Iterator[dict], total_count: int):
    """Writes a valid FNF JSON by preserving song metadata and streaming notes."""
    temp = out_path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as f:
        f.write('{"song":{')
        # Write all song keys (bpm, speed, etc) except notes
        meta_items = [f'"{k}":{json.dumps(v)}' for k, v in metadata.items() if k != "notes"]
        f.write(",".join(meta_items))
        f.write(',"notes":[')
        
        for i in range(total_count):
            try:
                sec = next(sections_iter)
                json.dump(sec, f, separators=(",", ":"))
                if i < total_count - 1: f.write(',')
            except StopIteration: break
            
        f.write(']}}')
    temp.rename(out_path)
    print(c(f"Saved → {out_path}", Color.YELLOW))

# =========================
# CORE FEATURES
# =========================

@timer
def append_notes(path: Path):
    chart = load_json(path)
    if not chart: return
    notes_pool = []
    for sec in chart["song"]["notes"]:
        if sec.get("sectionNotes"):
            notes_pool.extend(copy.deepcopy(sec["sectionNotes"]))
    
    for sec in chart["song"]["notes"]:
        if not sec.get("sectionNotes"):
            sec["sectionNotes"] = copy.deepcopy(notes_pool)
            
    _write_valid_fnf_json(path.parent / f"{path.stem}_appended.json", chart["song"], iter(chart["song"]["notes"]), len(chart["song"]["notes"]))

@timer
def merge_charts(paths: List[Path]):
    charts = [load_json(p) for p in paths if p.exists()]
    if not charts: return
    base = charts[0]
    all_sections = []
    for ch in charts:
        all_sections.extend(ch["song"]["notes"])
    
    _write_valid_fnf_json(paths[0].parent / "merged_chart.json", base["song"], iter(all_sections), len(all_sections))

@timer
def split_chart(path: Path, parts: int):
    chart = load_json(path)
    if not chart: return
    notes = chart["song"]["notes"]
    size = math.ceil(len(notes) / max(parts, 1))
    for i in range(parts):
        chunk = notes[i*size : (i+1)*size]
        if chunk:
            _write_valid_fnf_json(path.parent / f"{path.stem}_part{i+1}.json", chart["song"], iter(chunk), len(chunk))

@timer
def multiply_streaming(path: Path, multiplier: int):
    chart = load_json(path)
    if not chart or "song" not in chart: return
    
    orig_sections = chart["song"]["notes"]
    loop_ms = calculate_loop_ms(chart)
    total_count = len(orig_sections) * multiplier
    
    def offset_gen():
        for i in range(multiplier):
            ts_offset = i * loop_ms
            for sec in orig_sections:
                new_sec = copy.deepcopy(sec)
                if "sectionNotes" in new_sec:
                    for n in new_sec["sectionNotes"]:
                        n[0] += ts_offset # Shift the time!
                yield new_sec

    out_name = f"{path.stem}_x{multiplier}.json"
    _write_valid_fnf_json(path.parent / out_name, chart["song"], offset_gen(), total_count)

# =========================
# MENU SYSTEM
# =========================
def main():
    while True:
        print(c("\n--- FNF MULTITASK TOOL (ALL OPTIONS FIXED) ---", Color.MAGENTA))
        print("0 - Append (Fill empty sections)")
        print("1 - Merge (Combine multiple JSONs)")
        print("2 - Split (Divide chart into parts)")
        print("3 - Multiply (Safe + Time-Offset)")
        print("4 - Compress (Compact JSON format)")
        print("Q - Quit")
        
        choice = input("Select: ").upper().strip()
        
        if choice == "Q": break
        
        if choice in ["0", "2", "3", "4"]:
            p = clean_path(input("Path to JSON: "))
            if choice == "0": append_notes(p)
            elif choice == "2":
                parts = int(input("Number of parts: "))
                split_chart(p, parts)
            elif choice == "3":
                m = int(input("Multiplier: "))
                multiply_streaming(p, m)
            elif choice == "4":
                chart = load_json(p)
                if chart: _write_valid_fnf_json(p.parent / f"{p.stem}_compact.json", chart["song"], iter(chart["song"]["notes"]), len(chart["song"]["notes"]))
        
        elif choice == "1":
            raw = input("Paths (space separated): ")
            paths = [clean_path(x) for x in shlex.split(raw)]
            merge_charts(paths)

if __name__ == "__main__":
    main()

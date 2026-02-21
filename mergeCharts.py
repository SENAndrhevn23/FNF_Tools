#!/usr/bin/env python3
import json, copy, time, math, sys, os, shlex
from pathlib import Path
from urllib.parse import urlparse, unquote
from functools import wraps
from typing import Union, List, Iterator

# =========================
# CONFIG & COLORS
# =========================
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
        print(c(f"Error: {e}", Color.RED))
        return None

def calculate_song_ms(sections: List[dict], bpm: float) -> float:
    """Calculates total MS duration of a list of sections."""
    ms_per_beat = 60000 / bpm
    total_ms = 0
    for sec in sections:
        total_ms += sec.get("sectionBeats", 4) * ms_per_beat
    return total_ms

# =========================
# THE REPAIR ENGINE (STREAMING WRITER)
# =========================
def _write_valid_fnf_json(out_path: Path, song_obj: dict, sections_iter: Iterator[dict], total_count: int):
    """The core engine that prevents corruption and memory freezing."""
    temp = out_path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as f:
        f.write('{"song":{')
        meta_keys = [k for k in song_obj.keys() if k != "notes"]
        for i, k in enumerate(meta_keys):
            f.write(f'"{k}":{json.dumps(song_obj[k], separators=(",", ":"))}')
            f.write(',')
        
        f.write('"notes":[')
        for i in range(total_count):
            try:
                sec = next(sections_iter)
                json.dump(sec, f, separators=(",", ":"))
                if i < total_count - 1: f.write(",")
            except StopIteration: break
        f.write(']}}')
    
    if out_path.exists(): out_path.unlink()
    temp.rename(out_path)
    print(c(f"File Generated → {out_path.name}", Color.YELLOW))

# =========================
# FIXED CORE FEATURES
# =========================

@timer
def merge_charts_fixed(paths: List[Path]):
    """Merges multiple JSONs into 1 file and shifts timestamps so they play in order."""
    if not paths: return
    charts = [load_json(p) for p in paths if p.exists()]
    charts = [ch for ch in charts if ch and "song" in ch]
    if not charts: return

    base_metadata = charts[0]["song"]
    
    def merge_generator():
        current_offset_ms = 0
        for ch in charts:
            song_data = ch["song"]
            bpm = song_data.get("bpm", 100)
            sections = song_data.get("notes", [])
            
            for sec in sections:
                new_sec = copy.deepcopy(sec)
                if "sectionNotes" in new_sec:
                    for note in new_sec["sectionNotes"]:
                        note[0] += current_offset_ms # Shift time forward
                yield new_sec
            
            # Update offset for the next song in the merge
            current_offset_ms += calculate_song_ms(sections, bpm)

    total_sections = sum(len(ch["song"].get("notes", [])) for ch in charts)
    out_path = paths[0].parent / "MERGED_SONG.json"
    _write_valid_fnf_json(out_path, base_metadata, merge_generator(), total_sections)

@timer
def split_chart_fixed(path: Path, parts: int):
    """Splits a chart into parts instantly without hanging."""
    chart = load_json(path)
    if not chart or "song" not in chart: return
    
    sections = chart["song"]["notes"]
    total = len(sections)
    chunk_size = math.ceil(total / parts)

    for i in range(parts):
        start = i * chunk_size
        end = min(start + chunk_size, total)
        chunk = sections[start:end]
        
        if not chunk: break
        
        out_path = path.parent / f"{path.stem}_part{i+1}.json"
        # We pass a simple iterator of the slice to the writer
        _write_valid_fnf_json(out_path, chart["song"], iter(chunk), len(chunk))

@timer
def multiply_streaming_fixed(path: Path, multiplier: int):
    """The fixed multiplier with timestamp offsetting."""
    chart = load_json(path)
    if not chart: return
    
    orig_sections = chart["song"]["notes"]
    bpm = chart["song"].get("bpm", 100)
    loop_ms = calculate_song_ms(orig_sections, bpm)
    
    def mult_gen():
        for i in range(multiplier):
            offset = i * loop_ms
            for sec in orig_sections:
                new_sec = copy.deepcopy(sec)
                if "sectionNotes" in new_sec:
                    for n in new_sec["sectionNotes"]:
                        n[0] += offset
                yield new_sec

    total_count = len(orig_sections) * multiplier
    _write_valid_fnf_json(path.parent / f"{path.stem}_x{multiplier}.json", chart["song"], mult_gen(), total_count)

# =========================
# INTERFACE
# =========================
def main():
    while True:
        print(c("\n--- FNF TOOL: ULTIMATE REPAIR EDITION ---", Color.MAGENTA))
        print("1 - Merge (Join multiple JSONs into 1)")
        print("2 - Split (Divide JSON into parts - FAST)")
        print("3 - Multiply (Repeat song X times)")
        print("4 - Compress (Fix Corruption/Metadata)")
        print("Q - Quit")
        
        choice = input("Select: ").upper().strip()
        if choice == "Q": break
        
        if choice == "1":
            raw = input("Drop all files here (space separated): ")
            paths = [clean_path(x) for x in shlex.split(raw)]
            merge_charts_fixed(paths)
        elif choice == "2":
            p = clean_path(input("Path: "))
            n = int(input("How many parts?: "))
            split_chart_fixed(p, n)
        elif choice == "3":
            p = clean_path(input("Path: "))
            m = int(input("Multiplier: "))
            multiply_streaming_fixed(p, m)
        elif choice == "4":
            p = clean_path(input("Path: "))
            ch = load_json(p)
            if ch: _write_valid_fnf_json(p.parent/f"{p.stem}_fixed.json", ch["song"], iter(ch["song"]["notes"]), len(ch["song"]["notes"]))

if __name__ == "__main__":
    main()

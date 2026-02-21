#!/usr/bin/env python3
import json, copy, time, math, sys, os, shlex, gc
from pathlib import Path
from urllib.parse import urlparse, unquote
from functools import wraps
from typing import Union, List, Iterator

# =========================
# COLORS & LOGGING
# =========================
class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def c(text: str, color: str = Color.RESET) -> str:
    return f"{color}{text}{Color.RESET}"

# =========================
# DATA HELPERS
# =========================
def clean_path(p: str) -> Path:
    p = p.strip().strip('"').strip("'")
    if p.startswith("file://"):
        p = unquote(urlparse(p).path)
    return Path(os.path.normpath(os.path.expanduser(os.path.expandvars(p))))

def load_json_minimal(path: Path):
    if not path.exists(): return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data["song"] if "song" in data else data
    except Exception as e:
        print(c(f"Error: {e}", Color.RED))
        return None

def count_notes_in_sections(sections: List[dict]) -> int:
    count = 0
    for s in sections:
        if isinstance(s, dict) and "sectionNotes" in s:
            count += len(s["sectionNotes"])
    return count

# =========================
# THE STREAMING ENGINE
# =========================
def _write_and_report(out_path: Path, song_obj: dict, sections_iter: Iterator[dict], total_sections: int):
    temp = out_path.with_suffix(".tmp")
    final_note_count = 0
    
    try:
        with temp.open("w", encoding="utf-8") as f:
            f.write('{"song":{')
            meta = [f'"{k}":{json.dumps(v, separators=(",", ":"))}' for k, v in song_obj.items() if k != "notes"]
            f.write(",".join(meta) + ',"notes":[')
            
            for i in range(total_sections):
                try:
                    sec = next(sections_iter)
                    final_note_count += len(sec.get("sectionNotes", []))
                    json.dump(sec, f, separators=(",", ":"))
                    if i < total_sections - 1: f.write(",")
                    
                    # Small Progress Indicator for large files
                    if i % 100 == 0 and total_sections > 500:
                        percent = (i / total_sections) * 100
                        print(f"\rWriting: {percent:.1f}%", end="", flush=True)
                        
                except StopIteration: break
            
            f.write(']}}')
        
        print("\rWriting: 100%       ") # Clear progress line
        if out_path.exists(): out_path.unlink()
        temp.rename(out_path)
        return final_note_count
    except Exception as e:
        print(c(f"\nWrite Error: {e}", Color.RED))
        return 0

# =========================
# CORE TASKS
# =========================

def multiply_task(path: Path, m: int):
    song = load_json_minimal(path)
    if not song: return
    
    orig_sections = song.get("notes", [])
    before_count = count_notes_in_sections(orig_sections)
    
    bpm = song.get("bpm", 100)
    ms_per_beat = 60000 / bpm
    loop_ms = sum(s.get("sectionBeats", 4) for s in orig_sections) * ms_per_beat

    def mult_gen():
        for i in range(m):
            offset = i * loop_ms
            for sec in orig_sections:
                new_sec = copy.deepcopy(sec)
                if "sectionNotes" in new_sec:
                    for note in new_sec["sectionNotes"]:
                        note[0] += offset
                yield new_sec

    print(c(f"\nMultiplying chart x{m}...", Color.MAGENTA))
    total_secs = len(orig_sections) * m
    after_count = _write_and_report(path.parent / f"{path.stem}_x{m}.json", song, mult_gen(), total_secs)
    
    # --- YOUR REQUESTED SUMMARY ---
    print(c("=" * 30, Color.YELLOW))
    print(c(f"Notes Before: {before_count}", Color.CYAN))
    print(c(f"Notes After : {after_count}", Color.GREEN))
    print(c("=" * 30, Color.YELLOW))
    print(c(f"Result: {path.stem}_x{m}.json", Color.RESET))

def merge_task(paths: List[Path]):
    if not paths: return
    charts = [load_json_minimal(p) for p in paths if p.exists()]
    charts = [c for c in charts if c]
    
    total_before = sum(count_notes_in_sections(c.get("notes", [])) for c in charts)
    
    def merge_gen():
        offset = 0
        for ch in charts:
            bpm = ch.get("bpm", 100)
            ms_p_b = 60000 / bpm
            secs = ch.get("notes", [])
            for s in secs:
                ns = copy.deepcopy(s)
                if "sectionNotes" in ns:
                    for n in ns["sectionNotes"]: n[0] += offset
                yield ns
            offset += sum(s.get("sectionBeats", 4) for s in secs) * ms_p_b

    total_secs = sum(len(c.get("notes", [])) for c in charts)
    print(c(f"\nMerging {len(paths)} charts...", Color.MAGENTA))
    after = _write_and_report(paths[0].parent / "merged_result.json", charts[0], merge_gen(), total_secs)
    
    print(c("=" * 30, Color.YELLOW))
    print(c(f"Total Notes Before: {total_before}", Color.CYAN))
    print(c(f"Total Notes After : {after}", Color.GREEN))
    print(c("=" * 30, Color.YELLOW))

# =========================
# MAIN MENU
# =========================
def main():
    while True:
        print(c("\n[ FNF MULTI-TOOL: STREAMING EDITION ]", Color.MAGENTA))
        print("1 - Multiply (Show Before/After Count)")
        print("2 - Merge (Combine Multiple Files)")
        print("3 - Split (Fast Dividing)")
        print("4 - Repair (Fix JSON Corruption)")
        print("Q - Quit")
        
        choice = input("Select: ").upper().strip()
        if choice == 'Q': break
        
        try:
            if choice == "1":
                p = clean_path(input("Drag JSON here: "))
                m = int(input("Multiplier: "))
                multiply_task(p, m)
            elif choice == "2":
                raw = input("Drag all JSONs here: ")
                merge_task([clean_path(x) for x in shlex.split(raw)])
            elif choice == "3":
                p = clean_path(input("Drag JSON here: "))
                n = int(input("Parts: "))
                # Using the existing generator-based repair logic
                song = load_json_minimal(p)
                if song:
                    secs = song.get("notes", [])
                    chunk = math.ceil(len(secs) / n)
                    for i in range(n):
                        sub = secs[i*chunk : (i+1)*chunk]
                        _write_and_report(p.parent/f"{p.stem}_part{i+1}.json", song, iter(sub), len(sub))
                    print(c("Split complete!", Color.GREEN))
            elif choice == "4":
                p = clean_path(input("Drag JSON here: "))
                s = load_json_minimal(p)
                if s: _write_and_report(p.parent/f"{p.stem}_fixed.json", s, iter(s.get("notes", [])), len(s.get("notes", [])))
        except Exception as e:
            print(c(f"Critical Error: {e}", Color.RED))
        gc.collect()

if __name__ == "__main__":
    main()

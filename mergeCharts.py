#!/usr/bin/env python3
import json, copy, time, math, sys, os, shlex
from pathlib import Path
from urllib.parse import urlparse, unquote
from functools import wraps
from typing import Union, List, Iterator

# =========================
# CONFIG
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
# HELPERS
# =========================
def clean_path(p: Union[str, Path, None]) -> Path:
    if p is None: return Path(".")
    p = str(p).strip().strip('"').strip("'")
    if p.startswith("file://"):
        p = unquote(urlparse(p).path)
    return Path(os.path.normpath(os.path.expanduser(os.path.expandvars(p))))

def load_json(path: Path):
    if not path.exists(): return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def get_section_duration(section: dict) -> float:
    """Calculates duration of a section based on steps (standard FNF is 4 steps per beat)."""
    # Default: most sections are 16 steps long.
    return section.get("sectionBeats", 4) * 4 

def calculate_chart_duration_ms(chart: dict) -> float:
    """Estimates total chart duration in MS to offset notes correctly."""
    bpm = chart["song"].get("bpm", 100)
    ms_per_beat = 60000 / bpm
    total_ms = 0
    for sec in chart["song"]["notes"]:
        beats = sec.get("sectionBeats", 4)
        total_ms += beats * ms_per_beat
    return total_ms

# =========================
# FIXED STREAMING ENGINE
# =========================
def _iter_offset_sections(orig_sections: List[dict], multiplier: int, loop_duration_ms: float) -> Iterator[dict]:
    """Yields sections with notes shifted forward in time per repetition."""
    for i in range(multiplier):
        offset = i * loop_duration_ms
        for sec in orig_sections:
            # Deepcopy is necessary here because we are modifying timestamps
            new_sec = copy.deepcopy(sec)
            if "sectionNotes" in new_sec:
                for note in new_sec["sectionNotes"]:
                    # note[0] is the timestamp in MS
                    note[0] += offset
            yield new_sec

def _write_chart_streamed(out_path: Path, metadata: dict, sections_iter: Iterator[dict], total_count: int):
    """Writes a valid FNF JSON while streaming the massive notes array."""
    temp = out_path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as f:
        # Start the song object
        f.write('{"song": {')
        
        # Write all original metadata (bpm, speed, player1, etc.) EXCEPT the notes
        meta_items = [f'"{k}":{json.dumps(v)}' for k, v in metadata.items() if k != "notes"]
        f.write(",".join(meta_items))
        
        # Open the notes array
        f.write(',"notes":[')
        
        for i in range(total_count):
            try:
                sec = next(sections_iter)
                json.dump(sec, f, separators=(",", ":"))
                if i < total_count - 1:
                    f.write(",")
            except StopIteration:
                break
                
        # Close the notes array and the song object
        f.write(']}}')
    
    temp.rename(out_path)
    print(c(f"Saved → {out_path}", Color.YELLOW))

# =========================
# CORE FEATURES
# =========================
@timer
def multiply_logic(path: Path, multiplier: int):
    chart = load_json(path)
    if not chart or "song" not in chart:
        print(c("Invalid Chart Format!", Color.RED))
        return

    orig_sections = chart["song"]["notes"]
    loop_ms = calculate_chart_duration_ms(chart)
    total_sections = len(orig_sections) * multiplier
    
    # Prepare metadata (everything inside 'song' except the notes)
    song_metadata = chart["song"]
    
    out_dir = path.parent / "Multiplied_Charts"
    out_dir.mkdir(exist_ok=True)
    
    out_name = f"{path.stem}_x{multiplier}.json"
    sections_gen = _iter_offset_sections(orig_sections, multiplier, loop_ms)
    
    _write_chart_streamed(out_dir / out_name, song_metadata, sections_gen, total_sections)
    print(c(f"Success! Notes shifted by {loop_ms:.0f}ms per loop.", Color.GREEN))

# =========================
# MENU / MAIN
# =========================
def main():
    print(c("\nFNF MULTIPLIER FIX (Metadata + Timestamp Correction)", Color.MAGENTA))
    while True:
        print("-" * 30)
        p_input = input("Drag chart file here (or Q to quit): ").strip()
        if p_input.upper() == 'Q': break
        
        path = clean_path(p_input)
        if not path.exists():
            print(c("File not found!", Color.RED))
            continue
            
        try:
            mult = int(input("Multiplier (e.g. 2, 5, 10): "))
            multiply_logic(path, mult)
        except ValueError:
            print(c("Enter a valid number!", Color.RED))

if __name__ == "__main__":
    main()

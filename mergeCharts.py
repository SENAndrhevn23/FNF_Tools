#!/usr/bin/env python3
"""
FNF multiplier / timestamp shifter — improved and faster.

Usage:
    python3 fnf_multiplier.py /path/to/chart.json -m 5
or interactive:
    python3 fnf_multiplier.py
"""

import json
import time
import argparse
import os
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Iterator, List, Dict, Any

# -----------------------
# Config / ANSI colors
# -----------------------
MAX_WARN_SIZE_MB = 500  # warn if input is bigger than this (adjust as needed)

class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'

def c(text: str, color: str = Color.RESET) -> str:
    return f"{color}{text}{Color.RESET}"

# -----------------------
# Helpers
# -----------------------
def clean_path(p: str) -> Path:
    if not p:
        return Path(".")
    s = p.strip().strip('"').strip("'")
    if s.startswith("file://"):
        s = unquote(urlparse(s).path)
    return Path(os.path.normpath(os.path.expanduser(os.path.expandvars(s))))

def load_json(path: Path):
    if not path.exists():
        return None
    # Quick size check (warn)
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_WARN_SIZE_MB:
        print(c(f"Warning: input is large ({size_mb:.1f} MB). Loading into memory may take time.", Color.YELLOW))
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def get_bpm(chart: dict) -> float:
    return float(chart.get("song", {}).get("bpm", chart.get("bpm", 100)))

def calculate_chart_duration_ms(chart: dict) -> float:
    """
    Estimate total loop duration in ms.
    If sections include 'sectionBeats', use that (beats * ms_per_beat).
    Otherwise fallback to looking at max timestamp inside a section if present.
    Otherwise assume 4 beats per section.
    """
    bpm = get_bpm(chart)
    ms_per_beat = 60000.0 / bpm
    total_ms = 0.0
    sections = chart.get("song", {}).get("notes", [])
    for sec in sections:
        # Prefer explicit field
        beats = None
        if isinstance(sec, dict):
            beats = sec.get("sectionBeats", None)
        if beats is not None:
            total_ms += beats * ms_per_beat
            continue
        # Try to infer from timestamps inside sectionNotes
        timestamps = []
        if isinstance(sec, dict):
            notes = sec.get("sectionNotes", [])
            for n in notes:
                # note may be list [time, ...] or dict {'time':...}
                if isinstance(n, (list, tuple)) and len(n) > 0 and isinstance(n[0], (int, float)):
                    timestamps.append(float(n[0]))
                elif isinstance(n, dict) and "time" in n:
                    timestamps.append(float(n["time"]))
        if timestamps:
            # duration of this section: max ts - min ts (if they are ms)
            total_ms += max(timestamps) - min(timestamps)
        else:
            # fallback: 4 beats
            total_ms += 4 * ms_per_beat
    # Avoid zero
    return max(total_ms, 1.0)

# -----------------------
# Core: create adjusted section (fast, minimal copying)
# -----------------------
def offset_section(orig_section: Dict[str, Any], offset_ms: float) -> Dict[str, Any]:
    """
    Return a *new* section dict with note timestamps shifted by offset_ms.
    Only copies and modifies the notes array to reduce memory/time.
    Supports common formats:
      - section['sectionNotes'] = list of [time, ...] or dicts with 'time'
      - If structure is different, returns shallow copy unchanged.
    """
    if not isinstance(orig_section, dict):
        # unexpected format: return as-is
        return orig_section

    sec = dict(orig_section)  # shallow copy of section metadata
    if "sectionNotes" in orig_section and isinstance(orig_section["sectionNotes"], list):
        new_notes = []
        notes = orig_section["sectionNotes"]
        for n in notes:
            if isinstance(n, (list, tuple)) and len(n) > 0 and isinstance(n[0], (int, float)):
                # copy list/tuple, adjust first element (time)
                ln = list(n)
                ln[0] = ln[0] + offset_ms
                new_notes.append(ln)
            elif isinstance(n, dict) and "time" in n and isinstance(n["time"], (int, float)):
                nd = dict(n)
                nd["time"] = nd["time"] + offset_ms
                new_notes.append(nd)
            else:
                # If note format unknown, try leaving it unchanged (safer)
                new_notes.append(n)
        sec["sectionNotes"] = new_notes
    else:
        # maybe the section *is* a note structure (rare); try common fallback keys
        # For safety, we don't try to mutate arbitrary structures.
        pass
    return sec

def iter_offset_sections(orig_sections: List[Dict[str, Any]], multiplier: int, loop_duration_ms: float) -> Iterator[Dict[str, Any]]:
    """
    Yield each section repeated multiplier times with cumulative offsets applied.
    """
    for i in range(multiplier):
        offset = i * loop_duration_ms
        for sec in orig_sections:
            yield offset_section(sec, offset)

# -----------------------
# Streaming writer
# -----------------------
def write_chart_streamed(out_path: Path, song_metadata: Dict[str, Any], sections_iter: Iterator[Dict[str, Any]], total_sections: int):
    """
    Write output JSON streaming the notes array. This avoids building a giant list in memory.
    """
    tmp = out_path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write('{"song":{')
        # write metadata except 'notes'
        meta_items = []
        for k, v in song_metadata.items():
            if k == "notes":
                continue
            meta_items.append(f'"{k}":{json.dumps(v, separators=(",", ":"))}')
        f.write(",".join(meta_items))
        f.write(',"notes":[')

        written = 0
        start_t = time.time()
        # iterate and dump each section
        for sec in sections_iter:
            json.dump(sec, f, separators=(",", ":"))
            written += 1
            if written < total_sections:
                f.write(",")
            # occasional progress print
            if written % 500 == 0:
                elapsed = time.time() - start_t
                print(c(f"  Written {written}/{total_sections} sections — {elapsed:.1f}s", Color.MAGENTA))
        f.write(']}}')

    # atomic replace
    tmp.replace(out_path)
    print(c(f"Saved → {out_path}", Color.YELLOW))

# -----------------------
# Multiply logic (public)
# -----------------------
def multiply_logic(path: Path, multiplier: int, out_dir: Path = None):
    t0 = time.time()
    chart = load_json(path)
    if not chart or "song" not in chart:
        print(c("Invalid chart format (missing 'song')", Color.RED))
        return

    orig_sections = chart["song"].get("notes", [])
    if not isinstance(orig_sections, list) or len(orig_sections) == 0:
        print(c("No sections/notes found in chart.", Color.RED))
        return

    loop_ms = calculate_chart_duration_ms(chart)
    total_sections = len(orig_sections) * multiplier

    song_metadata = dict(chart["song"])  # shallow copy
    # remove notes from metadata (we will stream them)
    song_metadata.pop("notes", None)

    out_dir = out_dir or (path.parent / "Multiplied_Charts")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"{path.stem}_x{multiplier}.json"
    out_path = out_dir / out_name

    print(c(f"\nMultiplying {len(orig_sections)} sections × {multiplier} → {total_sections} total sections", Color.GREEN))
    print(c(f"Loop duration ≈ {loop_ms:.0f} ms (BPM: {get_bpm(chart):.2f})", Color.GREEN))
    print(c(f"Writing to: {out_path}", Color.YELLOW))

    sections_gen = iter_offset_sections(orig_sections, multiplier, loop_ms)
    write_chart_streamed(out_path, song_metadata, sections_gen, total_sections)

    elapsed = time.time() - t0
    print(c(f"Done in {elapsed:.2f}s — shifted notes by {loop_ms:.0f}ms per loop.", Color.GREEN))

# -----------------------
# CLI / interactive
# -----------------------
def main():
    parser = argparse.ArgumentParser(description="FNF chart multiplier / timestamp shifter")
    parser.add_argument("file", nargs="?", help="path to chart.json (drag & drop allowed)")
    parser.add_argument("-m", "--multiplier", type=int, default=2, help="how many times to repeat the chart")
    parser.add_argument("-o", "--outdir", help="output folder (optional)")
    args = parser.parse_args()

    if args.file:
        path = clean_path(args.file)
        if not path.exists():
            print(c("File not found!", Color.RED))
            return
        try:
            multiply_logic(path, args.multiplier, Path(args.outdir) if args.outdir else None)
        except Exception as e:
            print(c(f"Error: {e}", Color.RED))
    else:
        # interactive loop
        print(c("\nFNF MULTIPLIER (drag file, or type Q to quit)\n", Color.MAGENTA))
        while True:
            p_input = input("Chart file path (or Q to quit): ").strip()
            if p_input.upper() == "Q":
                break
            path = clean_path(p_input)
            if not path.exists():
                print(c("File not found!", Color.RED))
                continue
            try:
                mult = int(input("Multiplier (e.g. 2, 5, 10): ").strip())
                multiply_logic(path, mult)
            except ValueError:
                print(c("Enter a valid number for multiplier!", Color.RED))
            except Exception as e:
                print(c(f"Error: {e}", Color.RED))

if __name__ == "__main__":
    main()

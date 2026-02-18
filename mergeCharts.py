#!/usr/bin/env python3
"""
FNF MULTITASK TOOL — FAST MULTIPLIER (streaming) + PATH + SIZE OVERRIDE + STREAMED SAVE
Optimized: multiplier works by streaming repeated sections to disk instead of building
gigantic in-memory lists. Uses compact JSON separators to speed serialization.
"""

import json, copy, time, math, sys, os, shlex
from pathlib import Path
from urllib.parse import urlparse, unquote
from functools import wraps
from typing import Union, List, Iterator

# =========================
# CONFIG
# =========================
MAX_SIZE_MB = 1990  # 1.99 GB per file

# =========================
# COLORS / LOGGING
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
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            print(c(f"Error in {func.__name__}: {e}", Color.RED))
            raise
        print(c(f"Done in {time.time() - start:.2f}s\n", Color.GREEN))
        return result
    return wrapper

# =========================
# PATH HANDLING
# =========================
def clean_path(p: Union[str, Path, None]) -> Path:
    if p is None:
        return Path(".")
    if isinstance(p, Path):
        p = str(p)
    p = p.strip().strip('"').strip("'")
    if p.startswith("file://"):
        parsed = urlparse(p)
        path = unquote(parsed.path)
        if parsed.netloc:
            path = f"//{parsed.netloc}{path}"
        p = path
    p = os.path.expanduser(os.path.expandvars(p))
    return Path(os.path.normpath(p))

# =========================
# IO
# =========================
def load_json(path: Union[str, Path]):
    path = clean_path(path)
    if not path.exists():
        print(c(f"File not found: {path}", Color.RED))
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(c(f"JSON decode failed ({path}): {e}", Color.RED))
        return None
    except Exception as e:
        print(c(f"Failed to load JSON ({path}): {e}", Color.RED))
        return None

def save_json_stream(folder: Union[str, Path], name: str, chart, original_path: Path) -> Path:
    """
    Existing saver (keeps structure as chart contains it). Used for non-multiplied outputs.
    """
    out_dir = Path(original_path).parent / folder
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / name
    temp_file = out_file.with_suffix(".tmp")

    with temp_file.open("w", encoding="utf-8") as f:
        f.write('{"song":{"notes":[')
        notes = chart["song"]["notes"]
        for i, sec in enumerate(notes):
            json.dump(sec, f, ensure_ascii=False, separators=(",", ":"))
            if i != len(notes) - 1:
                f.write(',')
        f.write(']}}')

    temp_file.rename(out_file)
    print(c(f"Saved → {out_file}", Color.YELLOW))
    return out_file

def get_notes_count(chart) -> int:
    try:
        return sum(len(sec.get("sectionNotes", [])) for sec in chart["song"]["notes"])
    except Exception:
        # Fallback: count sections
        try:
            return len(chart["song"]["notes"])
        except Exception:
            return 0

def get_file_size_mb(path: Union[str, Path]) -> float:
    try:
        return clean_path(path).stat().st_size / (1024 * 1024)
    except Exception:
        return 0.0

# =========================
# VALIDATION
# =========================
def valid_chart(chart) -> bool:
    if not isinstance(chart, dict):
        return False
    if "song" in chart and isinstance(chart["song"], dict):
        song = chart["song"]
        if "notes" in song and isinstance(song["notes"], list):
            return True
        if "sections" in song and isinstance(song["sections"], list):
            chart["song"]["notes"] = song["sections"]
            return True
    if "notes" in chart and isinstance(chart["notes"], list):
        chart["song"] = {"notes": chart["notes"]}
        return True
    return False

# =========================
# SIZE CONFIRMATION
# =========================
def confirm_size_limit(path: Path, multiplier: int) -> bool:
    original_size = get_file_size_mb(path)
    estimated_size = original_size * multiplier
    if estimated_size > MAX_SIZE_MB:
        print(c(f"⚠ Estimated size {estimated_size:.2f} MB exceeds 1.99 GB limit!", Color.RED))
        resp = input("You sure you want to go above 1.99 GB? (Y/N): ").strip().upper()
        if resp != "Y":
            print(c("Operation canceled due to size limit.", Color.RED))
            return False
    return True

# =========================
# FEATURES (unchanged)
# =========================
@timer
def append_notes(path: Path):
    chart = load_json(path)
    if not chart or not valid_chart(chart):
        print(c("Failed to load chart!", Color.RED))
        return
    pool = []
    for sec in chart["song"]["notes"]:
        pool.extend(copy.deepcopy(sec.get("sectionNotes", [])))
    filled = 0
    for sec in chart["song"]["notes"]:
        if not sec.get("sectionNotes"):
            sec["sectionNotes"] = copy.deepcopy(pool)
            filled += 1
    save_json_stream("Append", f"{path.stem}_appended.json", chart, path)
    print(f"Sections filled: {filled}, Notes total: {get_notes_count(chart)}")

@timer
def merge_charts(paths: List[Union[str, Path]]):
    charts = []
    normalized_paths = []
    for p in paths:
        np = clean_path(p)
        normalized_paths.append(np)
        ch = load_json(np)
        if ch and valid_chart(ch):
            charts.append(ch)
        else:
            print(c(f"Skipping invalid chart: {np}", Color.RED))
    if not charts:
        print(c("No valid charts to merge", Color.RED))
        return
    base = copy.deepcopy(charts[0])
    for ch in charts[1:]:
        base["song"]["notes"].extend(copy.deepcopy(sec) for sec in ch["song"]["notes"])
    save_json_stream("Merged", "merged.json", base, normalized_paths[0])
    print(f"Merged {len(charts)} charts → {get_notes_count(base)} notes")

@timer
def split_chart(path: Path, parts: int):
    chart = load_json(path)
    if not chart or not valid_chart(chart):
        print(c("Failed to load chart!", Color.RED))
        return
    notes = chart["song"]["notes"]
    size = math.ceil(len(notes) / max(parts, 1))
    for i in range(parts):
        chunk = notes[i*size:(i+1)*size]
        if not chunk:
            continue
        new_chart = copy.deepcopy(chart)
        new_chart["song"]["notes"] = chunk
        save_json_stream("Split", f"{path.stem}_part{i+1}.json", new_chart, path)
        print(f"Part {i+1}: {get_notes_count(new_chart)} notes ({get_file_size_mb(path):.2f}MB)")

@timer
def compress_json(path: Path):
    chart = load_json(path)
    if not chart:
        return
    save_json_stream("Compressed", f"{path.stem}_compressed.json", chart, path)
    print("Compressed (structure unchanged)")

# =========================
# FAST MULTIPLY (STREAMING) & HELPERS
# =========================
def _iter_repeated_sections(orig_sections: List[dict], multiplier: int) -> Iterator[dict]:
    """
    Generator that yields sections repeated `multiplier` times.
    We do NOT deepcopy every repeated note in memory; instead we yield the same
    section object for serialization purposes. That is fine for file output,
    and avoids building giant structures in RAM.
    """
    for sec in orig_sections:
        # If you *must* guarantee unique objects per repetition inside Python memory,
        # replace the `yield sec` with `yield copy.deepcopy(sec)`.
        for _ in range(multiplier):
            yield sec

def _write_sections_to_file(out_path: Path, sections_iter: Iterator[dict], sections_count: int):
    """
    Writes exactly `sections_count` sections from the iterator into a single output file,
    wrapping them in {"song":{"notes":[ ... ]}} JSON object. Uses compact separators.
    """
    temp = out_path.with_suffix(".tmp")
    written = 0
    with temp.open("w", encoding="utf-8") as f:
        f.write('{"song":{"notes":[')
        first = True
        while written < sections_count:
            try:
                sec = next(sections_iter)
            except StopIteration:
                break
            if not first:
                f.write(',')
            json.dump(sec, f, ensure_ascii=False, separators=(",", ":"))
            first = False
            written += 1
        f.write(']}}')
    temp.rename(out_path)
    print(c(f"Saved → {out_path} ({written} sections)", Color.YELLOW))

@timer
def multiply_and_split_streaming(path: Path, multiplier: int, turbo: bool = False):
    """
    Streaming multiply that avoids expanding the whole chart in memory.
    If splits > 1 we create multiple output files, each containing a slice
    of the total repeated sections.
    """
    if not confirm_size_limit(path, multiplier):
        return
    chart = load_json(path)
    if not chart or not valid_chart(chart):
        print(c("Failed to load chart!", Color.RED))
        return

    original_sections = chart["song"]["notes"]
    orig_len = len(original_sections)
    total_sections = orig_len * max(multiplier, 1)
    print(c(f"Original sections: {orig_len}  →  Total after x{multiplier}: {total_sections}", Color.MAGENTA))

    # Ask for splits
    try:
        splits = int(input("Enter number of splits (1 for no split): "))
        if splits < 1:
            splits = 1
    except ValueError:
        splits = 1

    folder = "Multiply_TURBO" if turbo else "Multiply_SAFE"
    out_dir = Path(path).parent / folder
    out_dir.mkdir(parents=True, exist_ok=True)

    if splits == 1:
        # Create single output file by streaming all sections
        sections_iter = _iter_repeated_sections(original_sections, multiplier)
        out_name = f"{path.stem}_x{multiplier}_{'TURBO' if turbo else 'SAFE'}.json"
        _write_sections_to_file(out_dir / out_name, sections_iter, total_sections)
    else:
        # Compute per-part target sizes (make them roughly equal)
        per_part = math.ceil(total_sections / splits)
        sections_iter = _iter_repeated_sections(original_sections, multiplier)
        for i in range(splits):
            # For the last part, ensure we don't ask more than left (but _write will stop early on StopIteration)
            out_name = f"{path.stem}_x{multiplier}_{'TURBO' if turbo else 'SAFE'}_part{i+1}.json"
            _write_sections_to_file(out_dir / out_name, sections_iter, per_part)

    print(c(f"Multiply complete: x{multiplier} (streamed).", Color.GREEN))

@timer
def multiply_notes_safe(path: Path, multiplier: int):
    multiply_and_split_streaming(path, multiplier, turbo=False)

@timer
def multiply_notes_turbo(path: Path, multiplier: int):
    multiply_and_split_streaming(path, multiplier, turbo=True)

# =========================
# MENU
# =========================
def menu() -> str:
    print("""
===============================
FNF MULTITASK TOOL (FAST)
===============================
0 - Append notes
1 - Merge charts
2 - Split chart
3 - Multiply notes (SAFE, streaming) + optional splits
4 - Compress JSON
5 - Multiply notes (TURBO / UNSAFE, streaming) + optional splits
Q - Quit
""")
    return input("Select: ").upper().strip()

# =========================
# MAIN
# =========================
def main():
    while True:
        choice = menu()
        if choice == "Q":
            sys.exit(0)
        elif choice == "0":
            p = clean_path(input("Path: "))
            append_notes(p)
        elif choice == "1":
            raw = input("Charts (space-separated, quotes allowed): ").strip()
            if not raw:
                continue
            merge_charts(shlex.split(raw))
        elif choice == "2":
            p = clean_path(input("Path: "))
            try:
                n = int(input("Parts: "))
            except ValueError:
                print(c("Invalid number", Color.RED))
                continue
            split_chart(p, n)
        elif choice == "3":
            p = clean_path(input("Path: "))
            try:
                m = int(input("Multiplier: "))
            except ValueError:
                print(c("Invalid multiplier", Color.RED))
                continue
            multiply_notes_safe(p, m)
        elif choice == "4":
            p = clean_path(input("Path: "))
            compress_json(p)
        elif choice == "5":
            p = clean_path(input("Path: "))
            try:
                m = int(input("Multiplier: "))
            except ValueError:
                print(c("Invalid multiplier", Color.RED))
                continue
            multiply_notes_turbo(p, m)
        else:
            print(c("Unknown selection", Color.RED))

if __name__ == "__main__":
    print(c("FNF MULTITASK TOOL — FAST MULTIPLY (streaming) READY", Color.YELLOW))
    main()

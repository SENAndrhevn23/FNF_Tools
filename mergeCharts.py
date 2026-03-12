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
    """
    Load a JSON file and attempt to return a song-dictionary with 'notes' key.
    This function is defensive: it handles several common variants:
      - {"song": {...}}
      - {...} (already a song dict)
      - [ ... ] (list of sections/notes) -> wrapped as {"notes": [...]}
      - {"song": "<json-string>"} where the value is a JSON string -> parse it
    Returns None on error.
    """
    if not path.exists():
        print(c(f"File not found: {path}", Color.YELLOW))
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(c(f"JSON load error {path}: {e}", Color.RED))
        return None

    # If top-level is a dict
    if isinstance(data, dict):
        # common format: {"song": {...}}
        if "song" in data:
            song = data["song"]
            # sometimes "song" might be a JSON string (rare) -> try parse
            if isinstance(song, str):
                try:
                    parsed = json.loads(song)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    print(c("Found 'song' as string and couldn't parse it; skipping.", Color.YELLOW))
                    return None
            if isinstance(song, dict):
                return song
            # if it's a list inside "song", wrap appropriately
            if isinstance(song, list):
                return {"notes": song}
            # otherwise unknown shape
            print(c("Found 'song' field but its type is unexpected; skipping.", Color.YELLOW))
            return None

        # if it already looks like a song object (contains notes)
        if "notes" in data and isinstance(data["notes"], list):
            return data

        # other possible keys: 'chart', 'sections', etc. Try some heuristics:
        if "chart" in data and isinstance(data["chart"], dict):
            return data["chart"]
        if "sections" in data and isinstance(data["sections"], list):
            return {"notes": data["sections"], **{k: v for k, v in data.items() if k != "sections"}}

        # no obvious song-like structure -> return the dict anyway (caller will validate)
        return data

    # If top-level is a list, assume it's the "notes"/sections
    if isinstance(data, list):
        return {"notes": data}

    # Otherwise unknown
    print(c(f"Unsupported JSON root type in {path}: {type(data).__name__}", Color.YELLOW))
    return None

def count_notes_in_sections(sections: List[dict]) -> int:
    count = 0
    for s in sections:
        if isinstance(s, dict) and "sectionNotes" in s and isinstance(s["sectionNotes"], list):
            count += len(s["sectionNotes"])
        elif isinstance(s, list):
            # sometimes a section is just a list of notes
            count += len(s)
    return count

# =========================
# THE STREAMING ENGINE
# =========================
def _write_and_report(out_path: Path, song_obj: dict, sections_iter: Iterator[dict], total_sections: int):
    """
    Write a streaming JSON to out_path with the same top-level song metadata (except notes),
    streaming the 'notes' from sections_iter. Returns final_note_count.
    """
    # Ensure the song_obj is a dict
    if not isinstance(song_obj, dict):
        print(c("Warning: song_obj is not dict; coercing to {'notes': []}", Color.YELLOW))
        song_obj = {"notes": []}

    temp = out_path.with_suffix(".tmp")
    final_note_count = 0

    try:
        with temp.open("w", encoding="utf-8") as f:
            f.write('{"song":{')
            meta = []
            for k, v in song_obj.items():
                if k == "notes":
                    continue
                # Ensure keys are safe strings and values are json serialized compactly
                meta.append(f'"{k}":{json.dumps(v, separators=(",", ":"))}')
            f.write(",".join(meta) + ',"notes":[')

            for i in range(total_sections):
                try:
                    sec = next(sections_iter)
                except StopIteration:
                    break

                # Count notes in a section safely
                if isinstance(sec, dict):
                    section_notes = sec.get("sectionNotes", None)
                    if isinstance(section_notes, list):
                        final_note_count += len(section_notes)
                    else:
                        # maybe section directly stores notes as a list under other names
                        # try to guess: if sec itself appears to be a list-like container stored in dict, try length 0
                        pass
                elif isinstance(sec, list):
                    final_note_count += len(sec)
                else:
                    # unknown section type -> skip counting
                    pass

                # Dump the section as-is (json.dump can handle dicts/lists/primitives)
                try:
                    json.dump(sec, f, separators=(",", ":"))
                except TypeError:
                    # if sec contains non-serializable objects, convert to str fallback
                    json.dump(str(sec), f, separators=(",", ":"))

                if i < total_sections - 1:
                    f.write(",")

                # Small Progress Indicator for large files
                if i % 100 == 0 and total_sections > 500:
                    percent = (i / total_sections) * 100
                    print(f"\rWriting: {percent:.1f}%", end="", flush=True)

            f.write(']}}')

        print("\rWriting: 100%       ")  # Clear progress line
        if out_path.exists():
            try:
                out_path.unlink()
            except Exception:
                pass
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
    if not song or not isinstance(song, dict):
        print(c("Could not load song as dictionary. Aborting multiply.", Color.RED))
        return

    # Normalize sections to be dicts (skip malformed entries)
    orig_sections_raw = song.get("notes", [])
    orig_sections = [s for s in orig_sections_raw if isinstance(s, dict) or isinstance(s, list)]
    before_count = count_notes_in_sections(orig_sections)

    bpm = song.get("bpm", 100) if isinstance(song.get("bpm", None), (int, float)) else 100
    ms_per_beat = 60000 / bpm if bpm else 60000 / 100
    loop_ms = sum((s.get("sectionBeats", 4) if isinstance(s, dict) else 4) for s in orig_sections) * ms_per_beat

    def mult_gen():
        for i in range(m):
            offset = i * loop_ms
            for sec in orig_sections:
                new_sec = copy.deepcopy(sec)
                # If section is dict with "sectionNotes" increment timestamps safely
                if isinstance(new_sec, dict) and "sectionNotes" in new_sec and isinstance(new_sec["sectionNotes"], list):
                    for note in new_sec["sectionNotes"]:
                        # note may be a list like [time, ...]; ensure indexable and numeric
                        try:
                            if isinstance(note, list) and len(note) > 0 and isinstance(note[0], (int, float)):
                                note[0] = note[0] + offset
                        except Exception:
                            pass
                elif isinstance(new_sec, list):
                    # if section is a list of notes, try to shift numeric first element in each note
                    for note in new_sec:
                        try:
                            if isinstance(note, list) and len(note) > 0 and isinstance(note[0], (int, float)):
                                note[0] = note[0] + offset
                        except Exception:
                            pass
                yield new_sec

    print(c(f"\nMultiplying chart x{m}...", Color.MAGENTA))
    total_secs = len(orig_sections) * m
    out_file = path.parent / f"{path.stem}_x{m}.json"
    after_count = _write_and_report(out_file, song, mult_gen(), total_secs)

    # --- YOUR REQUESTED SUMMARY ---
    print(c("=" * 30, Color.YELLOW))
    print(c(f"Notes Before: {before_count}", Color.CYAN))
    print(c(f"Notes After : {after_count}", Color.GREEN))
    print(c("=" * 30, Color.YELLOW))
    print(c(f"Result: {out_file.name}", Color.RESET))

def merge_task(paths: List[Path]):
    if not paths:
        print(c("No paths provided to merge.", Color.YELLOW))
        return

    raw_charts = []
    for p in paths:
        if not p.exists():
            print(c(f"Skipping missing file: {p}", Color.YELLOW))
            continue
        loaded = load_json_minimal(p)
        if loaded:
            raw_charts.append((p, loaded))
        else:
            print(c(f"Could not parse: {p}", Color.YELLOW))

    if not raw_charts:
        print(c("No valid charts found to merge.", Color.RED))
        return

    # Normalize charts to dict structure
    charts = []
    for p, ch in raw_charts:
        if isinstance(ch, dict):
            charts.append(ch)
        elif isinstance(ch, list):
            charts.append({"notes": ch})
        else:
            print(c(f"Skipping chart {p} - unrecognized format.", Color.YELLOW))

    if not charts:
        print(c("No charts in recognizable format to merge.", Color.RED))
        return

    total_before = sum(count_notes_in_sections(c.get("notes", [])) for c in charts)

    def merge_gen():
        offset = 0
        for ch in charts:
            bpm = ch.get("bpm", 100) if isinstance(ch.get("bpm", None), (int, float)) else 100
            ms_p_b = 60000 / bpm if bpm else 60000 / 100
            secs = ch.get("notes", [])
            for s in secs:
                ns = copy.deepcopy(s)
                if isinstance(ns, dict) and "sectionNotes" in ns and isinstance(ns["sectionNotes"], list):
                    for n in ns["sectionNotes"]:
                        try:
                            if isinstance(n, list) and len(n) > 0 and isinstance(n[0], (int, float)):
                                n[0] += offset
                        except Exception:
                            pass
                elif isinstance(ns, list):
                    for n in ns:
                        try:
                            if isinstance(n, list) and len(n) > 0 and isinstance(n[0], (int, float)):
                                n[0] += offset
                        except Exception:
                            pass
                yield ns
            offset += sum((s.get("sectionBeats", 4) if isinstance(s, dict) else 4) for s in secs) * ms_p_b

    total_secs = sum(len(c.get("notes", [])) for c in charts)
    print(c(f"\nMerging {len(charts)} charts...", Color.MAGENTA))
    out_file = paths[0].parent / "merged_result.json"
    after = _write_and_report(out_file, charts[0], merge_gen(), total_secs)

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
        if choice == 'Q':
            break

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
                song = load_json_minimal(p)
                if song and isinstance(song, dict):
                    secs = [s for s in song.get("notes", []) if isinstance(s, (dict, list))]
                    if not secs:
                        print(c("No valid sections to split.", Color.YELLOW))
                        continue
                    chunk = math.ceil(len(secs) / n)
                    for i in range(n):
                        sub = secs[i*chunk : (i+1)*chunk]
                        _write_and_report(p.parent / f"{p.stem}_part{i+1}.json", song, iter(sub), len(sub))
                    print(c("Split complete!", Color.GREEN))
                else:
                    print(c("Could not load song for splitting.", Color.RED))
            elif choice == "4":
                p = clean_path(input("Drag JSON here: "))
                s = load_json_minimal(p)
                if s and isinstance(s, dict):
                    secs = [sct for sct in s.get("notes", []) if isinstance(sct, (dict, list))]
                    _write_and_report(p.parent / f"{p.stem}_fixed.json", s, iter(secs), len(secs))
                else:
                    print(c("Could not load file to repair.", Color.RED))
        except Exception as e:
            print(c(f"Critical Error: {e}", Color.RED))
        gc.collect()

if __name__ == "__main__":
    main()

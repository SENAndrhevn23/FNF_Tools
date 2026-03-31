#!/usr/bin/env python3
import json, copy, math, os, shlex, gc, gzip
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import List, Iterator

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
# PATH & JSON HELPERS
# =========================
def clean_path(p: str) -> Path:
    p = p.strip().strip('"').strip("'")
    if p.startswith("file://"):
        p = unquote(urlparse(p).path)
    return Path(os.path.normpath(os.path.expanduser(os.path.expandvars(p))))

def load_json_minimal(path: Path):
    if not path.exists():
        print(c(f"File not found: {path}", Color.YELLOW))
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(c(f"JSON load error: {e}", Color.RED))
        return None

    if isinstance(data, dict):
        if "song" in data and isinstance(data["song"], dict):
            return data["song"]
        if "notes" in data and isinstance(data["notes"], list):
            return data
        return {"notes": []}
    if isinstance(data, list):
        return {"notes": data}
    return {"notes": []}

def count_notes_in_sections(sections: List[dict]) -> int:
    count = 0
    for s in sections:
        if isinstance(s, dict) and "sectionNotes" in s and isinstance(s["sectionNotes"], list):
            count += len(s["sectionNotes"])
        elif isinstance(s, list):
            count += len(s)
    return count

# =========================
# WRITE STREAMING JSON
# =========================
def _write_and_report(out_path: Path, song_obj: dict, sections_iter: Iterator[dict], total_sections: int):
    temp = out_path.with_suffix(".tmp")
    final_note_count = 0
    try:
        with temp.open("w", encoding="utf-8") as f:
            f.write('{"song":{')
            meta = []
            for k, v in song_obj.items():
                if k == "notes": continue
                meta.append(f'"{k}":{json.dumps(v, separators=(",", ":"))}')
            f.write(",".join(meta) + ',"notes":[')
            for i in range(total_sections):
                try:
                    sec = next(sections_iter)
                except StopIteration:
                    break
                if isinstance(sec, dict) and "sectionNotes" in sec and isinstance(sec["sectionNotes"], list):
                    final_note_count += len(sec["sectionNotes"])
                elif isinstance(sec, list):
                    final_note_count += len(sec)
                try:
                    json.dump(sec, f, separators=(",", ":"))
                except TypeError:
                    json.dump(str(sec), f, separators=(",", ":"))
                if i < total_sections - 1:
                    f.write(",")
                if i % 100 == 0 and total_sections > 500:
                    percent = (i / total_sections) * 100
                    print(f"\rWriting: {percent:.1f}%", end="", flush=True)
            f.write(']}}')
        print("\rWriting: 100% ")
        if out_path.exists():
            try:
                out_path.unlink()
            except:
                pass
        temp.rename(out_path)
        return final_note_count
    except Exception as e:
        print(c(f"\nWrite Error: {e}", Color.RED))
        return 0

# =========================
# ADD NOTES FEATURE
# =========================
def add_notes_task():
    try:
        path = clean_path(input("Enter Json Path: ").strip())
        n = int(input("Enter Notes: ").strip())
        name = input("Enter Json Name: ").strip()
    except:
        print(c("Invalid input.", Color.RED))
        return

    song = {"notes": []}
    before_count = 0
    if path.exists():
        existing = load_json_minimal(path)
        if existing:
            song = existing
            before_count = count_notes_in_sections(song.get("notes", []))

    if not song["notes"]:
        song["notes"].append({"sectionNotes": []})

    section = song["notes"][0]
    if isinstance(section, dict) and "sectionNotes" in section:
        for _ in range(n):
            section["sectionNotes"].append([0,0])
    else:
        song["notes"].extend([[0,0] for _ in range(n)])

    out_file = path.parent / f"{name}.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump({"song": song}, f, separators=(",", ":"))

    after_count = count_notes_in_sections(song.get("notes", []))
    print("Adding Notes.. Done")
    print(f"Before: {before_count:,}")
    print(f"After : {after_count:,}")

# =========================
# MULTIPLY / LAYER
# =========================
def multiply_task(path: Path, multiplier: int):
    song = load_json_minimal(path)
    if not song or not isinstance(song, dict):
        print(c("Could not load song as dictionary. Aborting multiply.", Color.RED))
        return

    orig_sections = [s for s in song.get("notes", []) if isinstance(s, (dict, list))]
    before_count = count_notes_in_sections(orig_sections)

    print(c("\nFAST Layering mode (optimized)", Color.CYAN))

    try:
        offset_str = input("Time offset between layers (ms): ").strip()
        layer_offset_ms = float(offset_str) if offset_str else 0.0
    except:
        layer_offset_ms = 0.0

    def mult_gen():
        for i in range(multiplier):
            offset = i * layer_offset_ms
            for sec in orig_sections:
                if isinstance(sec, dict) and "sectionNotes" in sec:
                    new_sec = sec.copy()
                    new_notes = []
                    for note in sec["sectionNotes"]:
                        if isinstance(note, list):
                            n = note.copy()
                            if len(n) > 0:
                                n[0] += offset
                                n[0] = round(n[0], 2)
                            new_notes.append(n)
                        else:
                            new_notes.append(note)
                    new_sec["sectionNotes"] = new_notes
                    yield new_sec
                elif isinstance(sec, list):
                    new_notes = []
                    for note in sec:
                        if isinstance(note, list):
                            n = note.copy()
                            if len(n) > 0:
                                n[0] += offset
                                n[0] = round(n[0], 2)
                            new_notes.append(n)
                        else:
                            new_notes.append(note)
                    yield new_notes

    out_file = path.parent / f"{path.stem}_x{multiplier}.json"
    total_sections = len(orig_sections) * multiplier
    after_count = _write_and_report(out_file, song, mult_gen(), total_sections)

    print(c("Done (FAST).", Color.GREEN))
    print(f"Before: {before_count:,} notes")
    print(f"After : {after_count:,} notes  ({multiplier}x)")

# =========================
# MERGE
# =========================
def get_section_notes(section):
    if isinstance(section, dict) and isinstance(section.get("sectionNotes"), list):
        return section["sectionNotes"]
    if isinstance(section, list):
        return section
    return []

def save_chart_json(out_path: Path, chart: dict, compress: bool = False):
    temp = out_path.with_suffix(".tmp")
    if compress:
        with gzip.open(temp.with_suffix(".json.gz"), "wt", encoding="utf-8") as f:
            json.dump(chart, f, separators=(",", ":"))
    else:
        with temp.open("w", encoding="utf-8") as f:
            json.dump(chart, f, separators=(",", ":"))
    if out_path.exists():
        try: out_path.unlink()
        except: pass
    temp.rename(out_path)

def merge_task(paths: List[Path]):
    charts = []
    for p in paths:
        song = load_json_minimal(p)
        if song: charts.append(song)

    if not charts:
        print(c("No valid charts to merge.", Color.RED))
        return

    total_before = sum(count_notes_in_sections(ch.get("notes", [])) for ch in charts)

    base = copy.deepcopy(charts[0])
    max_sections = max(len(ch.get("notes", [])) for ch in charts)

    merged_sections = []

    for idx in range(max_sections):
        template = None
        combined_notes = []

        for ch in charts:
            notes = ch.get("notes", [])
            if idx >= len(notes): continue
            sec = notes[idx]
            if template is None and isinstance(sec, dict):
                template = copy.deepcopy(sec)
            elif template is None and isinstance(sec, list):
                template = {"sectionNotes": []}
            sec_notes = get_section_notes(sec)
            for note in sec_notes:
                combined_notes.append(copy.deepcopy(note))

        if template is None:
            template = {"gfSection": False, "altAnim": False, "sectionNotes": [], "bpm": base.get("bpm", 100), "sectionBeats": 4, "changeBPM": False, "mustHitSection": True}

        try:
            combined_notes.sort(key=lambda n: n[0] if isinstance(n, list) and len(n) > 0 else 0)
        except: pass

        if isinstance(template, dict):
            template["sectionNotes"] = combined_notes
        else:
            template = {"sectionNotes": combined_notes}

        merged_sections.append(template)

    merged_chart = copy.deepcopy(base)
    merged_chart["notes"] = merged_sections

    merged_events = []
    for ch in charts:
        ev = ch.get("events", [])
        if isinstance(ev, list):
            merged_events.extend(copy.deepcopy(ev))
    if merged_events:
        merged_chart["events"] = merged_events

    out_file = paths[0].parent / "merged_result.json"
    save_chart_json(out_file, merged_chart, compress=False)
    after_count = count_notes_in_sections(merged_chart.get("notes", []))

    print("Done.\n")
    print(f"Before: {total_before:,}")
    print(f"After : {after_count:,}")
    print(f"Saved : {out_file.name}")

# =========================
# SPLIT
# =========================
def split_task(path: Path, parts: int):
    song = load_json_minimal(path)
    if not song: return
    secs = [s for s in song.get("notes", []) if isinstance(s, (dict, list))]
    if not secs:
        print(c("No sections to split.", Color.YELLOW))
        return
    chunk = math.ceil(len(secs)/parts)
    for i in range(parts):
        sub = secs[i*chunk : (i+1)*chunk]
        out_file = path.parent / f"{path.stem}_part{i+1}.json"
        _write_and_report(out_file, song, iter(sub), len(sub))
    print("Split complete!")

# =========================
# REPAIR / COMPRESS
# =========================
def compressor_task(path: Path, compress: bool = False):
    song = load_json_minimal(path)
    if not song:
        print(c("No song data found.", Color.YELLOW))
        return

    def normalize_note(note):
        if isinstance(note, list) and len(note) > 0:
            note[0] = round(note[0], 2)
        return note

    def dedupe_notes(notes):
        seen = set()
        unique = []
        for n in notes:
            key = tuple(n) if isinstance(n, list) else str(n)
            if key not in seen:
                seen.add(key)
                unique.append(n)
        return unique

    sections = song.get("notes", [])
    fixed_sections = []

    for sec in sections:
        if isinstance(sec, dict) and "sectionNotes" in sec:
            new_notes = [
                normalize_note(n) for n in sec["sectionNotes"] if isinstance(n, list) and len(n) > 0
            ]
            new_notes = dedupe_notes(new_notes)
            sec["sectionNotes"] = new_notes
            sec.pop("altAnim", None)
            sec.pop("gfSection", None)
            fixed_sections.append(sec)
        elif isinstance(sec, list):
            new_sec = [
                normalize_note(n) for n in sec if isinstance(n, list) and len(n) > 0
            ]
            new_sec = dedupe_notes(new_sec)
            fixed_sections.append(new_sec)

    song["notes"] = fixed_sections
    out_file = path if not compress else path.with_suffix(".json.gz")
    try:
        if compress:
            with gzip.open(out_file, "wt", encoding="utf-8") as f:
                json.dump({"song": song}, f, separators=(",", ":"))
        else:
            with path.open("w", encoding="utf-8") as f:
                json.dump({"song": song}, f, separators=(",", ":"))
        print(c(f"Repair / Compression complete: {out_file.name}", Color.GREEN))
    except Exception as e:
        print(c(f"Compression Error: {e}", Color.RED))

# =========================
# MAIN MENU
# =========================
def main():
    while True:
        print(c("\n[ FNF MULTI-TOOL: STREAMING EDITION ]", Color.MAGENTA))
        print("1 - Multiply (layers / overlaps)")
        print("2 - Merge")
        print("3 - Split")
        print("4 - Repair / Compress")
        print("5 - Add Notes")
        print("Q - Quit")
        choice = input("Select: ").upper().strip()
        if choice == 'Q':
            break
        try:
            if choice == "1":
                p = clean_path(input("Enter Path: "))
                m_str = input("Enter Multiplier: ").strip()
                m = int(m_str) if m_str.isdigit() else 1
                multiply_task(p, m)
            elif choice == "2":
                raw = input("Enter all JSON paths (space-separated): ")
                merge_task([clean_path(x) for x in shlex.split(raw)])
            elif choice == "3":
                p = clean_path(input("Enter Path: "))
                n = int(input("Enter number of parts: "))
                split_task(p, n)
            elif choice == "4":
                p = clean_path(input("Enter Path: "))
                c_choice = input("Compress with gzip? (y/N): ").upper().strip()
                compressor_task(p, compress=(c_choice == "Y"))
            elif choice == "5":
                add_notes_task()
        except Exception as e:
            print(c(f"Critical Error: {e}", Color.RED))
        gc.collect()

if __name__ == "__main__":
    main()

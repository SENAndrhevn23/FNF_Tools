#!/usr/bin/env python3
import json
import os
import shlex
import subprocess
import random
import copy
from pathlib import Path
from urllib.parse import urlparse, unquote

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


def c(text, col=Color.RESET):
    return f"{col}{text}{Color.RESET}"


# =========================
# HELPERS
# =========================
def clean_path(p: str) -> Path:
    p = p.strip().strip('"').strip("'")
    if p.startswith("file://"):
        p = unquote(urlparse(p).path)
    return Path(os.path.normpath(os.path.expanduser(os.path.expandvars(p))))


def load_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(c(f"Load error: {e}", Color.RED))
        return None


def normalize_song(data):
    """
    Accepts:
    - {"song": {...}}
    - {...song...}
    - [sectionNotes...] fallback
    """
    if isinstance(data, dict) and "song" in data and isinstance(data["song"], dict):
        return data["song"]
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return {"notes": [{"sectionNotes": data}]}
    return None


def load_chart(path: Path):
    data = load_json(path)
    if data is None:
        return None
    song = normalize_song(data)
    if song is None:
        print(c("Unsupported chart format.", Color.RED))
    return song


def save_chart(path: Path, song):
    with path.open("w", encoding="utf-8") as f:
        json.dump({"song": song}, f, separators=(",", ":"), ensure_ascii=False)


def get_notes(sec):
    if isinstance(sec, dict):
        return sec.get("sectionNotes", [])
    if isinstance(sec, list):
        return sec
    return []


def set_notes(sec, notes):
    if isinstance(sec, dict):
        sec["sectionNotes"] = notes


def count_notes(song):
    return sum(len(get_notes(s)) for s in song.get("notes", []))


def pretty_size(num_bytes: int) -> str:
    mb = num_bytes / (1024 * 1024)
    if mb >= 1:
        txt = f"{mb:.1f}".rstrip("0").rstrip(".")
        return f"{txt}mb"
    kb = num_bytes / 1024
    if kb >= 1:
        txt = f"{kb:.1f}".rstrip("0").rstrip(".")
        return f"{txt}kb"
    return f"{num_bytes}b"


# =========================
# STREAM WRITER (SAFE)
# =========================
def write_stream(out: Path, generator, total: int):
    tmp = out.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write('{"song":{"notes":[')
        for i, sec in enumerate(generator):
            json.dump(sec, f, separators=(",", ":"))
            if i < total - 1:
                f.write(",")
            if i % 50 == 0:
                print(f"\rProcessing {i}/{total}", end="")
        f.write("]}}")

    if out.exists():
        out.unlink()
    tmp.rename(out)
    print("\n" + c("DONE", Color.GREEN))


# =========================
# 1 MERGE
# =========================
def merge_task(paths):
    charts = []
    for p in paths:
        chart = load_chart(p)
        if chart:
            charts.append(chart)

    if not charts:
        print(c("No valid charts loaded.", Color.RED))
        return

    max_len = max(len(chart.get("notes", [])) for chart in charts)

    def gen():
        for i in range(max_len):
            combined = []
            for chart in charts:
                notes_arr = chart.get("notes", [])
                if i < len(notes_arr):
                    combined += get_notes(notes_arr[i])
            yield {"sectionNotes": combined}

    write_stream(Path("merged.json"), gen(), max_len)


# =========================
# 2 MULTIPLY
# =========================
def multiply_task(path, mult):
    song = load_chart(path)
    if not song:
        return

    secs = song.get("notes", [])

    def gen():
        for sec in secs:
            notes = get_notes(sec)
            yield {"sectionNotes": notes * mult}

    write_stream(path.with_name(f"{path.stem}_x{mult}.json"), gen(), len(secs))


# =========================
# 3 SPLIT
# =========================
def split_task(path):
    song = load_chart(path)
    if not song:
        return

    secs = song.get("notes", [])

    parts = int(input("How many parts? ").strip())
    if parts < 2:
        print(c("Must be at least 2 parts.", Color.RED))
        return

    chunk_size = len(secs) // parts
    remainder = len(secs) % parts

    start = 0
    for i in range(parts):
        extra = 1 if i < remainder else 0
        end = start + chunk_size + extra

        out = path.with_name(f"{path.stem}_part{i+1}.json")
        save_chart(out, {"notes": secs[start:end]})

        start = end

    print(c(f"Split complete into {parts} parts", Color.GREEN))


# =========================
# 4 MINIFY
# =========================
def minify_task(path):
    song = load_chart(path)
    if not song:
        return
    save_chart(path.with_name("min.json"), song)
    print(c("Minified", Color.GREEN))


# =========================
# 5 ADD NOTES
# =========================
def add_notes_task(path, amount):
    song = load_chart(path)
    if not song:
        return

    for sec in song.get("notes", []):
        notes = get_notes(sec)
        for _ in range(amount):
            notes.append([random.randint(0, 200000), random.randint(0, 3), 0])

    save_chart(path.with_name("added.json"), song)
    print(c("Added notes", Color.GREEN))


# =========================
# 6 REMOVE NOTES
# =========================
def remove_notes_task(path):
    song = load_chart(path)
    if not song:
        return

    total = count_notes(song)

    print(f"Total Notes: {total:,}")
    print("1 End | 2 Start | 3 Random")

    mode = input("> ").strip()
    amt = int(input("Amount: ").strip())

    print("Deleting..")

    if mode == "1":  # END
        for sec in reversed(song.get("notes", [])):
            notes = get_notes(sec)
            take = min(len(notes), amt)
            del notes[-take:]
            amt -= take
            if amt <= 0:
                break

    elif mode == "2":  # START
        for sec in song.get("notes", []):
            notes = get_notes(sec)
            take = min(len(notes), amt)
            del notes[:take]
            amt -= take
            if amt <= 0:
                break

    elif mode == "3":  # RANDOM
        all_notes = []
        for sec in song.get("notes", []):
            all_notes.extend(get_notes(sec))

        remove_ids = set(random.sample(range(len(all_notes)), min(amt, len(all_notes))))

        i = 0
        for sec in song.get("notes", []):
            new = []
            for n in get_notes(sec):
                if i not in remove_ids:
                    new.append(n)
                i += 1
            set_notes(sec, new)

    save_chart(path.with_name("removed.json"), song)

    print("Done..")
    print(f"Notes: {count_notes(song):,}")


# =========================
# 7 COUNT
# =========================
def count_task(path):
    song = load_chart(path)
    if not song:
        return
    print(c(f"Notes: {count_notes(song):,}", Color.GREEN))


# =========================
# 8 MEDIA COMPRESS
# =========================
def media_task(path):
    out = path.with_suffix(".mp3")
    subprocess.run(["ffmpeg", "-y", "-i", str(path), "-b:a", "128k", str(out)])
    print(c("Compressed media", Color.GREEN))


# =========================
# 9 BLOATER
# =========================
def bloat_task(path):
    song = load_chart(path)
    if not song:
        return

    for sec in song.get("notes", []):
        if isinstance(sec, dict):
            sec["bloat"] = "0" * 10000

    save_chart(path.with_name("bloat.json"), song)
    print(c("Bloated", Color.YELLOW))


# =========================
# 10 CLEAN
# =========================
def clean_task(path):
    song = load_chart(path)
    if not song:
        return

    for sec in song.get("notes", []):
        if isinstance(sec, dict):
            sec.pop("bloat", None)

    save_chart(path.with_name("clean.json"), song)
    print(c("Cleaned", Color.GREEN))


# =========================
# 11 REAL COMBOS / NOTE MULTIPLIERS
# =========================
def is_multiplier_event_name(name: str) -> bool:
    n = name.strip().lower()
    return n in {
        "change combo",
        "change note multiplier",
        "note multiplier",
        "change note multipliers",
        "real combo",
    }


def extract_events_source(data):
    """
    Supports:
    - {"events": [...]}
    - {"song": {"events": [...]}}
    """
    if isinstance(data, dict):
        if isinstance(data.get("events"), list):
            return data["events"]
        if isinstance(data.get("song"), dict) and isinstance(data["song"].get("events"), list):
            return data["song"]["events"]
    return []


def parse_side_values(event_row):
    """
    Supports:
    ["Change Combo", "128", "128"]
    ["Change Note Multiplier", "2", ""]
    ["Change Combo", "", "2"]
    """
    if not isinstance(event_row, list) or not event_row:
        return 1.0, 1.0

    v1 = 1.0
    v2 = 1.0

    if len(event_row) > 1 and str(event_row[1]).strip() != "":
        try:
            v1 = float(event_row[1])
        except Exception:
            v1 = 1.0

    if len(event_row) > 2 and str(event_row[2]).strip() != "":
        try:
            v2 = float(event_row[2])
        except Exception:
            v2 = 1.0

    # If only one value exists, apply it to both sides.
    if v1 == 1.0 and v2 != 1.0:
        v1 = v2
    if v2 == 1.0 and v1 != 1.0:
        v2 = v1

    return v1, v2


def build_multiplier_timeline(events_data):
    raw_events = extract_events_source(events_data)
    timeline = []

    for block in raw_events:
        # Expected: [time, [[name, value1, value2], ...]]
        if not isinstance(block, list) or len(block) < 2:
            continue

        try:
            time_val = float(block[0])
        except Exception:
            continue

        inner = block[1]
        if not isinstance(inner, list):
            continue

        for event_row in inner:
            if not isinstance(event_row, list) or not event_row:
                continue

            name = str(event_row[0]).strip()
            if not is_multiplier_event_name(name):
                continue

            opp_mult, player_mult = parse_side_values(event_row)
            if opp_mult < 1:
                opp_mult = 1
            if player_mult < 1:
                player_mult = 1

            timeline.append((time_val, opp_mult, player_mult))

    timeline.sort(key=lambda x: x[0])
    return timeline


def multiplier_for_time(note_time, timeline):
    opp_mult = 1
    player_mult = 1

    for t, o, p in timeline:
        if note_time >= t:
            opp_mult = o
            player_mult = p
        else:
            break

    return opp_mult, player_mult


def remove_multiplier_events(song):
    events = song.get("events")
    if not isinstance(events, list):
        return

    kept = []
    for block in events:
        if not isinstance(block, list) or len(block) < 2:
            kept.append(block)
            continue

        inner = block[1]
        if not isinstance(inner, list):
            kept.append(block)
            continue

        has_multiplier = False
        for event_row in inner:
            if isinstance(event_row, list) and event_row:
                name = str(event_row[0]).strip()
                if is_multiplier_event_name(name):
                    has_multiplier = True
                    break

        if not has_multiplier:
            kept.append(block)

    song["events"] = kept


def is_player_section(section):
    if isinstance(section, dict):
        return bool(section.get("mustHitSection", True))
    return True


def real_combo_task(events_path, json_path):
    events_data = load_json(events_path)
    if events_data is None:
        return

    song = load_chart(json_path)
    if not song:
        return

    timeline = build_multiplier_timeline(events_data)
    if not timeline:
        print(c("No Change Combo / Note Multiplier events found.", Color.RED))
        return

    before_notes = count_notes(song)
    before_size = json_path.stat().st_size

    print("Turning into real notes..")

    new_song = copy.deepcopy(song)
    remove_multiplier_events(new_song)

    for sec in new_song.get("notes", []):
        notes = get_notes(sec)
        if not notes:
            continue

        player_section = is_player_section(sec)
        expanded = []

        for note in notes:
            if not isinstance(note, list) or not note:
                continue

            try:
                note_time = float(note[0])
            except Exception:
                note_time = 0.0

            opp_mult, player_mult = multiplier_for_time(note_time, timeline)
            mult = player_mult if player_section else opp_mult
            mult = max(1, int(round(mult)))

            for _ in range(mult):
                expanded.append(copy.deepcopy(note))

        set_notes(sec, expanded)

    out = json_path.with_name(f"{json_path.stem}_real_notes.json")
    save_chart(out, new_song)

    after_notes = count_notes(new_song)
    after_size = out.stat().st_size

    print(c("Done", Color.GREEN))
    print(f"Before: {before_notes:,}")
    print(f"After: {after_notes:,}")
    print(f"Size Before: {pretty_size(before_size)}")
    print(f"Size After: {pretty_size(after_size)}")
    print(f"Saved To: {out}")


# =========================
# MAIN
# =========================
def main():
    while True:
        print(c("\n--- FNF TOOL ---", Color.MAGENTA))
        print("1 Merge   2 Multiply   3 Split   4 Minify")
        print("5 Add     6 Remove     7 Count   8 Media")
        print("9 Bloat   10 Clean     11 Real Combos   Q Quit")

        ch = input("> ").upper().strip()

        try:
            if ch == "1":
                merge_task([clean_path(x) for x in shlex.split(input("Paths: "))])
            elif ch == "2":
                multiply_task(clean_path(input("Path: ")), int(input("Multiplier: ")))
            elif ch == "3":
                split_task(clean_path(input("Path: ")))
            elif ch == "4":
                minify_task(clean_path(input("Path: ")))
            elif ch == "5":
                add_notes_task(clean_path(input("Path: ")), int(input("Amount: ")))
            elif ch == "6":
                remove_notes_task(clean_path(input("Path: ")))
            elif ch == "7":
                count_task(clean_path(input("Path: ")))
            elif ch == "8":
                media_task(clean_path(input("File: ")))
            elif ch == "9":
                bloat_task(clean_path(input("Path: ")))
            elif ch == "10":
                clean_task(clean_path(input("Path: ")))
            elif ch == "11":
                events_path = clean_path(input("Enter Events Path: "))
                json_path = clean_path(input("Enter Json Path: "))
                real_combo_task(events_path, json_path)
            elif ch == "Q":
                break
        except Exception as e:
            print(c(f"Error: {e}", Color.RED))


if __name__ == "__main__":
    main()

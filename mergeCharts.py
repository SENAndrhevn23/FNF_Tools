#!/usr/bin/env python3
import argparse
import copy
import json
import os
import random
import shlex
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote


# =========================
# COLORS
# =========================
class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    RESET = "\033[0m"


USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def c(text, col=Color.RESET):
    if not USE_COLOR:
        return str(text)
    return f"{col}{text}{Color.RESET}"


# =========================
# HELPERS
# =========================
def clean_path(p: str) -> Path:
    p = str(p).strip().strip('"').strip("'")
    if p.startswith("file://"):
        p = unquote(urlparse(p).path)
    return Path(os.path.normpath(os.path.expanduser(os.path.expandvars(p))))


def prompt(text: str):
    try:
        return input(text)
    except EOFError:
        return None


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
    path.parent.mkdir(parents=True, exist_ok=True)
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


def default_output(path: Path, suffix: str, ext: str = ".json") -> Path:
    return path.with_name(f"{path.stem}{suffix}{ext}")


# =========================
# STREAM WRITER (SAFE)
# =========================
def write_stream(out: Path, generator, total: int):
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write('{"song":{"notes":[')
        for i, sec in enumerate(generator):
            json.dump(sec, f, separators=(",", ":"), ensure_ascii=False)
            if i < total - 1:
                f.write(",")
            if total and i % 50 == 0:
                print(f"\rProcessing {i}/{total}", end="")
        f.write("]}}")

    if out.exists():
        out.unlink()
    tmp.rename(out)
    print("\n" + c("DONE", Color.GREEN))


# =========================
# 1 MERGE
# =========================
def merge_task(paths, out_path: Path | None = None):
    charts = []
    for p in paths:
        chart = load_chart(p)
        if chart:
            charts.append(chart)

    if not charts:
        print(c("No valid charts loaded.", Color.RED))
        return 1

    max_len = max(len(chart.get("notes", [])) for chart in charts)
    out_path = out_path or Path("merged.json")

    def gen():
        for i in range(max_len):
            combined = []
            for chart in charts:
                notes_arr = chart.get("notes", [])
                if i < len(notes_arr):
                    combined += get_notes(notes_arr[i])
            yield {"sectionNotes": combined}

    write_stream(out_path, gen(), max_len)
    print(c(f"Saved to: {out_path}", Color.GREEN))
    return 0


# =========================
# 2 MULTIPLY
# =========================
def multiply_task(path, mult, out_path: Path | None = None):
    song = load_chart(path)
    if not song:
        return 1

    secs = song.get("notes", [])
    out_path = out_path or path.with_name(f"{path.stem}_x{mult}.json")

    def gen():
        for sec in secs:
            notes = get_notes(sec)
            yield {"sectionNotes": notes * mult}

    write_stream(out_path, gen(), len(secs))
    print(c(f"Saved to: {out_path}", Color.GREEN))
    return 0


# =========================
# 3 SPLIT
# =========================
def split_task(path, parts: int | None = None, out_dir: Path | None = None):
    song = load_chart(path)
    if not song:
        return 1

    secs = song.get("notes", [])

    if parts is None:
        raw = prompt("How many parts? ")
        if raw is None:
            print(c("No input available for split parts.", Color.RED))
            return 1
        parts = int(raw.strip())

    if parts < 2:
        print(c("Must be at least 2 parts.", Color.RED))
        return 1

    out_dir = out_dir or path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    chunk_size = len(secs) // parts
    remainder = len(secs) % parts

    start = 0
    for i in range(parts):
        extra = 1 if i < remainder else 0
        end = start + chunk_size + extra

        out = out_dir / f"{path.stem}_part{i+1}.json"
        save_chart(out, {"notes": secs[start:end]})
        start = end

    print(c(f"Split complete into {parts} parts", Color.GREEN))
    return 0


# =========================
# 4 MINIFY
# =========================
def minify_task(path, out_path: Path | None = None):
    song = load_chart(path)
    if not song:
        return 1
    out_path = out_path or path.with_name("min.json")
    save_chart(out_path, song)
    print(c(f"Minified -> {out_path}", Color.GREEN))
    return 0


# =========================
# 5 ADD NOTES
# =========================
def add_notes_task(path, amount, out_path: Path | None = None):
    song = load_chart(path)
    if not song:
        return 1

    for sec in song.get("notes", []):
        notes = get_notes(sec)
        for _ in range(amount):
            notes.append([random.randint(0, 200000), random.randint(0, 3), 0])

    out_path = out_path or path.with_name("added.json")
    save_chart(out_path, song)
    print(c(f"Added notes -> {out_path}", Color.GREEN))
    return 0


# =========================
# 6 REMOVE NOTES
# =========================
def remove_notes_task(path, mode: str | None = None, amt: int | None = None, out_path: Path | None = None):
    song = load_chart(path)
    if not song:
        return 1

    total = count_notes(song)
    print(f"Total Notes: {total:,}")
    print("1 End | 2 Start | 3 Random")

    if mode is None:
        mode = prompt("> ")
        if mode is None:
            print(c("No input available for remove mode.", Color.RED))
            return 1
        mode = mode.strip()

    if amt is None:
        raw_amt = prompt("Amount: ")
        if raw_amt is None:
            print(c("No input available for amount.", Color.RED))
            return 1
        amt = int(raw_amt.strip())

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
    else:
        print(c("Invalid mode. Use 1, 2, or 3.", Color.RED))
        return 1

    out_path = out_path or path.with_name("removed.json")
    save_chart(out_path, song)

    print("Done..")
    print(f"Notes: {count_notes(song):,}")
    print(c(f"Saved to: {out_path}", Color.GREEN))
    return 0


# =========================
# 7 COUNT
# =========================
def count_task(path):
    song = load_chart(path)
    if not song:
        return 1
    print(c(f"Notes: {count_notes(song):,}", Color.GREEN))
    return 0


# =========================
# 8 MEDIA COMPRESS
# =========================
def media_task(path, out_path: Path | None = None, bitrate: str = "128k"):
    out_path = out_path or path.with_suffix(".mp3")
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-b:a", bitrate, str(out_path)],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print(c("ffmpeg not found on PATH.", Color.RED))
        return 1

    if result.returncode != 0:
        print(c("ffmpeg failed.", Color.RED))
        if result.stderr:
            print(result.stderr)
        return result.returncode

    print(c(f"Compressed media -> {out_path}", Color.GREEN))
    return 0


# =========================
# 9 BLOATER
# =========================
def bloat_task(path, out_path: Path | None = None):
    song = load_chart(path)
    if not song:
        return 1

    for sec in song.get("notes", []):
        if isinstance(sec, dict):
            sec["bloat"] = "0" * 10000

    out_path = out_path or path.with_name("bloat.json")
    save_chart(out_path, song)
    print(c(f"Bloated -> {out_path}", Color.YELLOW))
    return 0


# =========================
# 10 CLEAN
# =========================
def clean_task(path, out_path: Path | None = None):
    song = load_chart(path)
    if not song:
        return 1

    for sec in song.get("notes", []):
        if isinstance(sec, dict):
            sec.pop("bloat", None)

    out_path = out_path or path.with_name("clean.json")
    save_chart(out_path, song)
    print(c(f"Cleaned -> {out_path}", Color.GREEN))
    return 0


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
        if isinstance(data.get("song"), dict) and isinstance(data.get("song", {}).get("events"), list):
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
            opp_mult = max(1, opp_mult)
            player_mult = max(1, player_mult)
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


def real_combo_task(events_path, json_path, out_path: Path | None = None):
    events_data = load_json(events_path)
    if events_data is None:
        return 1

    song = load_chart(json_path)
    if not song:
        return 1

    timeline = build_multiplier_timeline(events_data)
    if not timeline:
        print(c("No Change Combo / Note Multiplier events found.", Color.RED))
        return 1

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

    out_path = out_path or json_path.with_name(f"{json_path.stem}_real_notes.json")
    save_chart(out_path, new_song)

    after_notes = count_notes(new_song)
    after_size = out_path.stat().st_size

    print(c("Done", Color.GREEN))
    print(f"Before: {before_notes:,}")
    print(f"After: {after_notes:,}")
    print(f"Size Before: {pretty_size(before_size)}")
    print(f"Size After: {pretty_size(after_size)}")
    print(f"Saved To: {out_path}")
    return 0


# =========================
# INTERACTIVE MENU
# =========================
def interactive_menu():
    while True:
        print(c("\n--- FNF TOOL ---", Color.MAGENTA))
        print("1 Merge   2 Multiply   3 Split   4 Minify")
        print("5 Add     6 Remove     7 Count   8 Media")
        print("9 Bloat   10 Clean     11 Real Combos   Q Quit")

        ch = prompt("> ")
        if ch is None:
            print(c("No interactive input available. Use command-line arguments.", Color.RED))
            return 1

        ch = ch.upper().strip()

        try:
            if ch == "1":
                raw = prompt("Paths: ")
                if raw is None:
                    raise RuntimeError("No paths entered.")
                merge_task([clean_path(x) for x in shlex.split(raw)])
            elif ch == "2":
                multiply_task(clean_path(prompt("Path: ") or ""), int(prompt("Multiplier: ") or "1"))
            elif ch == "3":
                split_task(clean_path(prompt("Path: ") or ""))
            elif ch == "4":
                minify_task(clean_path(prompt("Path: ") or ""))
            elif ch == "5":
                add_notes_task(clean_path(prompt("Path: ") or ""), int(prompt("Amount: ") or "0"))
            elif ch == "6":
                remove_notes_task(clean_path(prompt("Path: ") or ""))
            elif ch == "7":
                count_task(clean_path(prompt("Path: ") or ""))
            elif ch == "8":
                media_task(clean_path(prompt("File: ") or ""))
            elif ch == "9":
                bloat_task(clean_path(prompt("Path: ") or ""))
            elif ch == "10":
                clean_task(clean_path(prompt("Path: ") or ""))
            elif ch == "11":
                events_path = clean_path(prompt("Enter Events Path: ") or "")
                json_path = clean_path(prompt("Enter Json Path: ") or "")
                real_combo_task(events_path, json_path)
            elif ch == "Q":
                return 0
        except Exception as e:
            print(c(f"Error: {e}", Color.RED))


# =========================
# CLI
# =========================
def build_parser():
    p = argparse.ArgumentParser(prog="mergeCharts.py", description="FNF chart utility tool")
    sub = p.add_subparsers(dest="cmd")

    m = sub.add_parser("merge", help="Merge multiple charts")
    m.add_argument("paths", nargs="+")
    m.add_argument("-o", "--out", default="merged.json")

    m = sub.add_parser("multiply", help="Multiply notes in each section")
    m.add_argument("path")
    m.add_argument("mult", type=int)
    m.add_argument("-o", "--out")

    m = sub.add_parser("split", help="Split chart into parts")
    m.add_argument("path")
    m.add_argument("--parts", type=int)
    m.add_argument("-d", "--dir")

    m = sub.add_parser("minify", help="Save chart as min.json")
    m.add_argument("path")
    m.add_argument("-o", "--out")

    m = sub.add_parser("add", help="Add random notes")
    m.add_argument("path")
    m.add_argument("amount", type=int)
    m.add_argument("-o", "--out")

    m = sub.add_parser("remove", help="Remove notes")
    m.add_argument("path")
    m.add_argument("--mode", choices=["1", "2", "3"])
    m.add_argument("--amount", type=int)
    m.add_argument("-o", "--out")

    m = sub.add_parser("count", help="Count notes")
    m.add_argument("path")

    m = sub.add_parser("media", help="Compress media to mp3")
    m.add_argument("path")
    m.add_argument("-o", "--out")
    m.add_argument("--bitrate", default="128k")

    m = sub.add_parser("bloat", help="Add bloat field to sections")
    m.add_argument("path")
    m.add_argument("-o", "--out")

    m = sub.add_parser("clean", help="Remove bloat field from sections")
    m.add_argument("path")
    m.add_argument("-o", "--out")

    m = sub.add_parser("real-combos", help="Expand note multipliers into real notes")
    m.add_argument("events_path")
    m.add_argument("json_path")
    m.add_argument("-o", "--out")

    return p


def run_cli(args) -> int:
    if args.cmd == "merge":
        return merge_task([clean_path(x) for x in args.paths], clean_path(args.out))
    if args.cmd == "multiply":
        return multiply_task(clean_path(args.path), args.mult, clean_path(args.out) if args.out else None)
    if args.cmd == "split":
        return split_task(
            clean_path(args.path),
            args.parts,
            clean_path(args.dir) if args.dir else None,
        )
    if args.cmd == "minify":
        return minify_task(clean_path(args.path), clean_path(args.out) if args.out else None)
    if args.cmd == "add":
        return add_notes_task(clean_path(args.path), args.amount, clean_path(args.out) if args.out else None)
    if args.cmd == "remove":
        return remove_notes_task(
            clean_path(args.path),
            args.mode,
            args.amount,
            clean_path(args.out) if args.out else None,
        )
    if args.cmd == "count":
        return count_task(clean_path(args.path))
    if args.cmd == "media":
        return media_task(clean_path(args.path), clean_path(args.out) if args.out else None, args.bitrate)
    if args.cmd == "bloat":
        return bloat_task(clean_path(args.path), clean_path(args.out) if args.out else None)
    if args.cmd == "clean":
        return clean_task(clean_path(args.path), clean_path(args.out) if args.out else None)
    if args.cmd == "real-combos":
        return real_combo_task(
            clean_path(args.events_path),
            clean_path(args.json_path),
            clean_path(args.out) if args.out else None,
        )
    return 0


# =========================
# MAIN
# =========================
def main():
    parser = build_parser()

    # No args:
    # - interactive if attached to a terminal
    # - otherwise print help and exit cleanly for CI
    if len(sys.argv) == 1:
        if sys.stdin.isatty():
            return interactive_menu()
        parser.print_help()
        return 0

    args = parser.parse_args()
    if not args.cmd:
        if sys.stdin.isatty():
            return interactive_menu()
        parser.print_help()
        return 2

    try:
        return run_cli(args)
    except Exception as e:
        print(c(f"Error: {e}", Color.RED))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

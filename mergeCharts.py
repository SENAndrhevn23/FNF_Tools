import json
import copy
import time
from pathlib import Path
import argparse

# =========================
# TRY IMPORTS
# =========================
try:
    from pydub import AudioSegment
    import numpy as np
    AUDIO_SUPPORT = True
except ImportError:
    AUDIO_SUPPORT = False

# =========================
# UTILITIES
# =========================
class Color:
    GREEN = '\033[92m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

def c(text, color=Color.RESET):
    return f"{color}{text}{Color.RESET}"

def elapsed_fmt(seconds):
    return f"{seconds:.2f}s"

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        print(c(f"\nStarting: {func.__name__}", Color.MAGENTA))
        res = func(*args, **kwargs)
        end = time.time()
        print(c(f"Completed: {func.__name__} in {elapsed_fmt(end-start)}", Color.GREEN))
        return res
    return wrapper

def clean_path(path: str) -> str:
    return path.strip().strip('"').strip("'")

def make_folder(name: str) -> Path:
    path = ROOT_FOLDER / name
    path.mkdir(exist_ok=True)
    return path

def compress_json(data):
    return json.dumps(data, separators=(",", ":"))

# =========================
# CONFIG
# =========================
ROOT_FOLDER = Path(r"C:\Users\andre\Documents\CHARTS")
ROOT_FOLDER.mkdir(exist_ok=True)

# =========================
# ARGUMENTS
# =========================
parser = argparse.ArgumentParser(description="FNF Multitask Tool")
parser.add_argument("--action", type=str, help="Menu choice (0-10, Q)")
parser.add_argument("--file", type=str, help="Path to chart JSON")
parser.add_argument("--multiply", type=int, help="Multiplier for notes")
parser.add_argument("--show-updates", action="store_true", help="Show menu and exit immediately")
args = parser.parse_args()

# =========================
# MENU
# =========================
def show_menu():
    menu_text = """
========================================
FNF MULTITASK TOOL
========================================
0: Append Notes to Empty Sections
1: Merge Charts
2: Split Chart
3: Multiply Notes (Fast & Compressed)
4: Ultra-Compress JSON
5: NPS Fill
6: Load Large Charts (sorted)
7: MIDI to FNF Chart
8: Dynamic Note Multiplier
9: Multi-Pass JSON Compression
10: Audio to FNF Chart
Q: Quit
"""
    print(menu_text)

    if args.show_updates:
        print("⚡ CLI show-updates mode: menu displayed and exiting.")
        exit(0)

    if args.action:
        return args.action.upper()

    return input("Choose an option (0-10/Q): ").strip().upper()

# =========================
# FUNCTIONS
# =========================

@timer
def append_notes():
    path = Path(args.file if args.file else clean_path(input("Enter path to JSON file: ")))
    if not path.exists():
        print(c(f"❌ File not found: {path}", Color.RED))
        return
    folder_path = make_folder("AppendNotes_Folder")
    with path.open("r", encoding="utf-8") as f:
        chart = json.load(f)

    all_notes = []
    for section in chart["song"]["notes"]:
        all_notes.extend(copy.deepcopy(section.get("sectionNotes", [])))

    empty_sections = [s for s in chart["song"]["notes"] if not s.get("sectionNotes")]
    for section in empty_sections:
        section["sectionNotes"] = copy.deepcopy(all_notes)

    new_file = folder_path / f"{path.stem}_appended.json"
    with new_file.open("w", encoding="utf-8") as f:
        json.dump(chart, f, indent=4)

    print(f"✅ Appended notes to {len(empty_sections)} empty sections.")
    print(f"Saved as {new_file}")

@timer
def merge_charts():
    file_paths = []
    while True:
        f = clean_path(input("Enter path of chart to merge (or 'stop'): "))
        if f.lower() == "stop":
            break
        f_path = Path(f)
        if not f_path.exists():
            print(c(f"❌ File not found: {f}", Color.RED))
        else:
            file_paths.append(f_path)
    if not file_paths:
        print(c("❌ No valid files provided!", Color.RED))
        return

    folder_path = make_folder("Merged_Folder")
    output_name = input("Output filename (without .json): ").strip() or "merged_chart"
    merged_chart = None
    for idx, f in enumerate(file_paths):
        with f.open("r", encoding="utf-8") as file:
            chart = json.load(file)
        if idx == 0:
            merged_chart = copy.deepcopy(chart)
        else:
            merged_chart["song"]["notes"].extend(chart["song"].get("notes", []))

    out_file = folder_path / f"{output_name}.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(merged_chart, f, indent=4)

    total_notes = sum(len(section["sectionNotes"]) for section in merged_chart["song"]["notes"])
    print(f"✅ Merged {len(file_paths)} charts into {len(merged_chart['song']['notes'])} sections, {total_notes} notes.")
    print(f"Saved in {folder_path}")

@timer
def split_chart():
    path = Path(clean_path(input("Enter path to chart to split: ")))
    if not path.exists():
        print(c(f"❌ File not found: {path}", Color.RED))
        return
    folder_path = make_folder("Split_Folder")
    output_name = input("Base filename (without .json): ").strip() or "split_chart"

    try:
        splits = int(input("How many splits: ").strip())
        if splits < 2:
            raise ValueError
    except ValueError:
        print(c("❌ Please enter a valid number greater than 1!", Color.RED))
        return

    with path.open("r", encoding="utf-8") as f:
        base = json.load(f)

    total_sections = len(base["song"]["notes"])
    if splits > total_sections:
        splits = total_sections

    chunk_size = total_sections // splits
    remainder = total_sections % splits
    start = 0
    for i in range(splits):
        end = start + chunk_size + (1 if i < remainder else 0)
        new_chart = copy.deepcopy(base)
        new_chart["song"]["notes"] = base["song"]["notes"][start:end]
        output_file = folder_path / f"{output_name}-{i+1}.json"
        with output_file.open("w", encoding="utf-8") as out:
            json.dump(new_chart, f, indent=4)
        print(f"{output_file}: {len(new_chart['song']['notes'])} sections")
        start = end
    print("✅ Done.")

@timer
def multiply_notes_fast_compressed():
    try:
        import orjson
    except ImportError:
        print(c("❌ orjson not installed! Run: pip install orjson", Color.RED))
        return

    path = Path(clean_path(input("Enter path to chart: ")))
    if not path.exists():
        print(c(f"❌ File not found: {path}", Color.RED))
        return

    folder_path = make_folder("Multiply_FastCompressed")

    try:
        multiplier = int(input("Enter multiplier (>=2): ").strip())
        if multiplier < 2:
            raise ValueError
    except ValueError:
        print(c("❌ Invalid multiplier!", Color.RED))
        return

    out_file = folder_path / f"{path.stem}_x{multiplier}_STREAM.json"

    # ⏱️ Start streaming
    t_start = time.time()
    with path.open("r", encoding="utf-8") as f, out_file.open("wb") as out:
        chart = orjson.loads(f.read())
        song = chart["song"]

        # Write header
        header = {
            "player1": song.get("player1", "bf"),
            "player2": song.get("player2", "dad")
        }
        out.write(b'{"song":')
        out.write(orjson.dumps(header)[:-1])  # remove closing }
        out.write(b',"notes":[')

        first_section = True
        for s in song["notes"]:
            notes = s.get("sectionNotes", [])
            if notes:
                section_bytes = orjson.dumps({"sectionNotes": notes * multiplier})
                if not first_section:
                    out.write(b',')
                out.write(section_bytes[1:-1])  # remove outer {}
                first_section = False

        out.write(b']}}')

    t_end = time.time()
    print(c(f"✅ Done. Elapsed time: {t_end - t_start:.2f}s", Color.GREEN))
    total_notes = sum(len(s.get("sectionNotes", [])) * multiplier for s in song["notes"])
    print(c(f"Total notes: {total_notes}", Color.GREEN))
    print(f"Saved in {out_file}")


@timer
def ultra_compress_json():
    path = Path(clean_path(input("Enter path to chart: ")))
    if not path.exists():
        print(c(f"❌ File not found: {path}", Color.RED))
        return
    folder_path = make_folder("UltraCompress_Folder")
    with path.open("r", encoding="utf-8") as f:
        chart = json.load(f)

    prev_size = None
    current_chart = chart
    while True:
        compressed_str = compress_json(current_chart)
        new_size = len(compressed_str.encode("utf-8"))
        if prev_size and new_size >= prev_size * 0.98:
            break
        prev_size = new_size
        current_chart = json.loads(compressed_str)

    new_file = folder_path / f"{path.stem}_ultracompressed.json"
    with new_file.open("w", encoding="utf-8") as f:
        json.dump(current_chart, f, indent=2)
    print(f"✅ Done. Final size: {new_file.stat().st_size / (1024*1024):.2f} MB")
    print(f"Saved in {new_file}")

# =========================
# MAIN LOOP
# =========================
def main():
    while True:
        choice = show_menu()
        if choice == "Q":
            print("Exiting...")
            break
        elif choice == "0":
            append_notes()
        elif choice == "1":
            merge_charts()
        elif choice == "2":
            split_chart()
        elif choice == "3":
            multiply_notes_fast_compressed()
        elif choice == "4":
            ultra_compress_json()
        else:
            print(c("❌ Invalid choice!", Color.RED))

if __name__ == "__main__":
    print(c("FNF MULTITASK TOOL (Version: 0.3.1)", Color.YELLOW))
    print(c("Warning: Large multipliers can produce huge files!", Color.RED))
    main()



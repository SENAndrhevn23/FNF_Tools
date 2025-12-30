import json
import copy
import time
from pathlib import Path
import argparse
import sys

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

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        print(c(f"\nStarting: {func.__name__}", Color.MAGENTA))
        result = func(*args, **kwargs)
        print(c(f"Completed in {time.time() - start:.2f}s", Color.GREEN))
        return result
    return wrapper

def clean_path(path: str) -> str:
    return path.strip().strip('"').strip("'")

def make_folder(name: str) -> Path:
    path = ROOT_FOLDER / name
    path.mkdir(parents=True, exist_ok=True)
    return path

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(c(f"JSON error: {e}", Color.RED))
        return None

# =========================
# CONFIG (PORTABLE)
# =========================
ROOT_FOLDER = Path.cwd() / "CHARTS"
ROOT_FOLDER.mkdir(parents=True, exist_ok=True)

# =========================
# ARGUMENTS
# =========================
parser = argparse.ArgumentParser(description="FNF Multitask Chart Tool")
parser.add_argument("--action", help="0-4 or Q")
parser.add_argument("--file", help="Chart JSON file")
parser.add_argument("--multiply", type=int, help="Multiplier (>=2)")
parser.add_argument("--split", type=int, help="Split count")
parser.add_argument("--merge", nargs="*", help="Charts to merge")
args = parser.parse_args()

# =========================
# MENU
# =========================
def show_menu():
    print("""
========================================
FNF MULTITASK TOOL (STABLE)
========================================
0: Append Notes to Empty Sections
1: Merge Charts
2: Split Chart
3: Multiply Notes (SAFE)
4: Compress JSON
Q: Quit
""")
    return input("Choose: ").strip().upper()

# =========================
# FUNCTIONS
# =========================
@timer
def append_notes(path: Path):
    chart = load_json(path)
    if not chart:
        return

    all_notes = []
    for sec in chart["song"]["notes"]:
        all_notes.extend(copy.deepcopy(sec.get("sectionNotes", [])))

    count = 0
    for sec in chart["song"]["notes"]:
        if not sec.get("sectionNotes"):
            sec["sectionNotes"] = copy.deepcopy(all_notes)
            count += 1

    out = make_folder("AppendNotes") / f"{path.stem}_appended.json"
    out.write_text(json.dumps(chart, indent=4))
    print(f"✅ Appended notes to {count} sections")

@timer
def merge_charts(paths):
    charts = []
    for p in paths:
        chart = load_json(Path(p))
        if chart:
            charts.append(chart)

    if not charts:
        print(c("No valid charts", Color.RED))
        return

    base = charts[0]
    for c2 in charts[1:]:
        base["song"]["notes"].extend(c2["song"]["notes"])

    out = make_folder("Merged") / "merged.json"
    out.write_text(json.dumps(base, indent=4))
    print(f"✅ Merged {len(charts)} charts")

@timer
def split_chart(path: Path, splits: int):
    chart = load_json(path)
    if not chart or splits < 2:
        return

    notes = chart["song"]["notes"]
    size = len(notes) // splits
    folder = make_folder("Split")

    for i in range(splits):
        new_chart = copy.deepcopy(chart)
        new_chart["song"]["notes"] = notes[i*size:(i+1)*size]
        out = folder / f"{path.stem}_part{i+1}.json"
        out.write_text(json.dumps(new_chart, indent=4))
        print(f"Saved {out.name}")

@timer
def multiply_notes(path: Path, multiplier: int):
    if multiplier < 2:
        print(c("Multiplier must be >= 2", Color.RED))
        return

    chart = load_json(path)
    if not chart:
        return

    for sec in chart["song"]["notes"]:
        if sec.get("sectionNotes"):
            sec["sectionNotes"] *= multiplier

    out = make_folder("Multiply") / f"{path.stem}_x{multiplier}.json"
    out.write_text(json.dumps(chart, indent=4))
    print(f"✅ Notes multiplied x{multiplier}")

@timer
def compress_json(path: Path):
    chart = load_json(path)
    if not chart:
        return

    out = make_folder("Compressed") / f"{path.stem}_compressed.json"
    out.write_text(json.dumps(chart, separators=(",", ":")))
    print("✅ JSON compressed")

# =========================
# MAIN
# =========================
def main():
    if args.action:
        action = args.action.upper()

        if action == "0" and args.file:
            append_notes(Path(clean_path(args.file)))
        elif action == "1" and args.merge:
            merge_charts(args.merge)
        elif action == "2" and args.file and args.split:
            split_chart(Path(clean_path(args.file)), args.split)
        elif action == "3" and args.file and args.multiply:
            multiply_notes(Path(clean_path(args.file)), args.multiply)
        elif action == "4" and args.file:
            compress_json(Path(clean_path(args.file)))
        else:
            print(c("Invalid CLI usage", Color.RED))
        return

    # Interactive mode
    while True:
        choice = show_menu()
        if choice == "Q":
            break
        elif choice == "0":
            append_notes(Path(clean_path(input("JSON path: "))))
        elif choice == "1":
            merge_charts(input("Charts (space separated): ").split())
        elif choice == "2":
            split_chart(
                Path(clean_path(input("JSON path: "))),
                int(input("Splits: "))
            )
        elif choice == "3":
            multiply_notes(
                Path(clean_path(input("JSON path: "))),
                int(input("Multiplier: "))
            )
        elif choice == "4":
            compress_json(Path(clean_path(input("JSON path: "))))
        else:
            print(c("Invalid choice", Color.RED))

if __name__ == "__main__":
    print(c("FNF MULTITASK TOOL – CI SAFE BUILD", Color.YELLOW))
    main()

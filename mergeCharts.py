import json
import copy
import time
from pathlib import Path
import argparse

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
        res = func(*args, **kwargs)
        print(c(f"Completed in {time.time()-start:.2f}s", Color.GREEN))
        return res
    return wrapper

def clean_path(path: str) -> str:
    return path.strip().strip('"').strip("'")

def make_folder(name: str) -> Path:
    path = ROOT_FOLDER / name
    path.mkdir(exist_ok=True)
    return path

# =========================
# CONFIG
# =========================
ROOT_FOLDER = Path(r"C:\Users\andre\Documents\CHARTS")
ROOT_FOLDER.mkdir(exist_ok=True)

# =========================
# ARGUMENTS
# =========================
parser = argparse.ArgumentParser(description="FNF Multitask Tool")
parser.add_argument("--action", type=str)
parser.add_argument("--file", type=str)
parser.add_argument("--multiply", type=int)
args = parser.parse_args()

# =========================
# MENU
# =========================
def show_menu():
    print("""
========================================
FNF MULTITASK TOOL (FIXED)
========================================
0: Append Notes to Empty Sections
1: Merge Charts
2: Split Chart
3: Multiply Notes (SAFE)
4: Compress JSON (Valid)
Q: Quit
""")
    return args.action.upper() if args.action else input("Choose: ").strip().upper()

# =========================
# FUNCTIONS
# =========================

@timer
def append_notes():
    path = Path(args.file or clean_path(input("JSON path: ")))
    if not path.exists():
        print(c("File not found", Color.RED))
        return

    chart = json.loads(path.read_text(encoding="utf-8"))

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
def merge_charts():
    paths = []
    while True:
        p = clean_path(input("Chart path (or stop): "))
        if p.lower() == "stop":
            break
        if Path(p).exists():
            paths.append(Path(p))

    if not paths:
        print(c("No charts provided", Color.RED))
        return

    base = json.loads(paths[0].read_text(encoding="utf-8"))
    for p in paths[1:]:
        base["song"]["notes"].extend(
            json.loads(p.read_text(encoding="utf-8"))["song"]["notes"]
        )

    out = make_folder("Merged") / "merged.json"
    out.write_text(json.dumps(base, indent=4))
    print(f"✅ Merged {len(paths)} charts")

@timer
def split_chart():
    path = Path(clean_path(input("Chart path: ")))
    if not path.exists():
        print(c("File not found", Color.RED))
        return

    splits = int(input("Number of splits: "))
    chart = json.loads(path.read_text(encoding="utf-8"))

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
def multiply_notes_safe():
    path = Path(args.file or clean_path(input("Chart path: ")))
    if not path.exists():
        print(c("File not found", Color.RED))
        return

    multiplier = args.multiply or int(input("Multiplier >=2: "))
    if multiplier < 2:
        print(c("Invalid multiplier", Color.RED))
        return

    chart = json.loads(path.read_text(encoding="utf-8"))

    for sec in chart["song"]["notes"]:
        if sec.get("sectionNotes"):
            sec["sectionNotes"] *= multiplier

    out = make_folder("Multiply") / f"{path.stem}_x{multiplier}.json"
    out.write_text(json.dumps(chart, indent=4))
    print(f"✅ Notes multiplied x{multiplier}")

@timer
def compress_json():
    path = Path(clean_path(input("Chart path: ")))
    if not path.exists():
        print(c("File not found", Color.RED))
        return

    chart = json.loads(path.read_text(encoding="utf-8"))
    out = make_folder("Compressed") / f"{path.stem}_compressed.json"
    out.write_text(json.dumps(chart, separators=(",", ":")))
    print("✅ JSON compressed (valid)")

# =========================
# MAIN
# =========================
def main():
    while True:
        choice = show_menu()
        if choice == "Q":
            break
        elif choice == "0":
            append_notes()
        elif choice == "1":
            merge_charts()
        elif choice == "2":
            split_chart()
        elif choice == "3":
            multiply_notes_safe()
        elif choice == "4":
            compress_json()
        else:
            print(c("Invalid choice", Color.RED))

if __name__ == "__main__":
    print(c("FNF MULTITASK TOOL – STABLE BUILD", Color.YELLOW))
    main()

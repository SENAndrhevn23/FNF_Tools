#!/usr/bin/env python3
# FULL OPTIMIZED FNF TOOL + MEDIA COMPRESSOR

import json, math, os, shlex, gzip, subprocess, shutil
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import List, Iterator

# =========================
# COLORS
# =========================
class Color:
    GREEN='\033[92m'; RED='\033[91m'; YELLOW='\033[93m'
    MAGENTA='\033[95m'; CYAN='\033[96m'; RESET='\033[0m'

def c(t, col=Color.RESET): return f"{col}{t}{Color.RESET}"

# =========================
# PATH
# =========================
def clean_path(p:str)->Path:
    p=p.strip().strip('"').strip("'")
    if p.startswith("file://"): p=unquote(urlparse(p).path)
    return Path(os.path.normpath(os.path.expanduser(os.path.expandvars(p))))

# =========================
# LOAD JSON
# =========================
def load_json_minimal(path:Path):
    if not path.exists():
        print(c(f"Missing: {path}",Color.YELLOW)); return None
    try:
        with path.open("r",encoding="utf-8") as f:
            d=json.load(f)
    except Exception as e:
        print(c(f"Load error: {e}",Color.RED)); return None

    if isinstance(d,dict):
        if "song" in d: return d["song"]
        return d
    if isinstance(d,list): return {"notes":d}
    return None

# =========================
# HELPERS
# =========================
def get_notes(sec):
    if isinstance(sec,dict): return sec.get("sectionNotes",[])
    if isinstance(sec,list): return sec
    return []

# =========================
# STREAM WRITE
# =========================
def write_stream(out:Path, base:dict, gen:Iterator, total:int):
    tmp=out.with_suffix(".tmp")
    with tmp.open("w",encoding="utf-8") as f:
        f.write('{"song":{')

        first=True
        for k,v in base.items():
            if k=="notes": continue
            if not first: f.write(",")
            f.write(f'"{k}":{json.dumps(v,separators=(",",":"))}')
            first=False

        f.write(',"notes":[')

        for i,sec in enumerate(gen):
            json.dump(sec,f,separators=(",",":"))
            if i<total-1: f.write(",")
            if i%100==0: print(f"\rWriting {i}/{total}",end="")

        f.write(']}}')

    if out.exists(): out.unlink()
    tmp.rename(out)
    print("\nDone")

# =========================
# NOTE COUNT
# =========================
def count_notes_task(path: Path):
    song = load_json_minimal(path)
    if not song: return

    total_notes = 0
    for sec in song.get("notes", []):
        total_notes += len(get_notes(sec))

    print(c("-"*20, Color.CYAN))
    print(f"Chart: {c(path.name, Color.YELLOW)}")
    print(f"Total Notes: {c(total_notes, Color.GREEN)}")
    print(c("-"*20, Color.CYAN))

# =========================
# MERGE
# =========================
def merge_task(paths:List[Path]):
    charts=[load_json_minimal(p) for p in paths]
    charts=[c for c in charts if c]
    if not charts:
        print(c("No charts",Color.RED)); return

    base=charts[0]
    max_sec=max(len(c.get("notes",[])) for c in charts)

    print(c("FAST MERGE",Color.CYAN))
    do_sort=input("Sort notes? (y/N): ").upper().strip()=="Y"

    def gen():
        for i in range(max_sec):
            combined=[]
            template=None

            for ch in charts:
                secs=ch.get("notes",[])
                if i>=len(secs): continue

                sec=secs[i]
                if template is None:
                    template=dict(sec) if isinstance(sec,dict) else {"sectionNotes":[]}

                combined.extend(get_notes(sec))

            if do_sort:
                combined.sort(key=lambda x:x[0] if isinstance(x,list) else 0)

            template["sectionNotes"]=combined
            yield template

    out=paths[0].parent/"merged_fast.json"
    write_stream(out,base,gen(),max_sec)

# =========================
# MULTIPLY
# =========================
def multiply_task(path:Path,m:int):
    song=load_json_minimal(path)
    if not song: return

    secs=song.get("notes",[])

    def gen():
        for sec in secs:
            notes=get_notes(sec)
            if not notes:
                yield sec; continue

            new=[]
            for n in notes:
                new.extend([n]*m)

            if isinstance(sec,dict):
                s=dict(sec); s["sectionNotes"]=new; yield s
            else:
                yield new

    out=path.parent/f"{path.stem}_x{m}.json"
    write_stream(out,song,gen(),len(secs))

# =========================
# COMPRESS JSON (OPTIMIZE)
# =========================
def compress_task(path: Path):
    song = load_json_minimal(path)
    if not song: return

    def optimize_note(n):
        return [int(x) if isinstance(x, float) and x.is_integer() else x for x in n]

    def optimize():
        for sec in song.get("notes", []):
            notes = get_notes(sec)
            new_notes = [optimize_note(n) for n in notes]
            if isinstance(sec, dict):
                s=dict(sec)
                s["sectionNotes"]=new_notes
                yield s
            else:
                yield new_notes

    out = path.parent / f"{path.stem}_optimized.json"
    write_stream(out, song, optimize(), len(song.get("notes", [])))
    print("JSON optimized")

# =========================
# 🎬 MEDIA COMPRESSOR (NEW)
# =========================
def compress_media_task(path: Path):
    if not path.exists():
        print(c("File not found", Color.RED))
        return

    size_before = path.stat().st_size / (1024 * 1024)

    print(c(f"Video Path: {path}", Color.CYAN))
    print("Compressing...")

    ext = path.suffix.lower()

    if ext in [".mp3", ".wav", ".ogg", ".flac"]:
        out_file = path.with_suffix(".mp3")
        cmd = [
            "ffmpeg","-y","-i",str(path),
            "-b:a","128k",str(out_file)
        ]
    else:
        out_file = path.with_name(path.stem + "_compressed.mp4")
        cmd = [
            "ffmpeg","-y","-i",str(path),
            "-vcodec","libx264",
            "-crf","28",
            "-preset","fast",
            "-acodec","aac",
            "-b:a","128k",
            str(out_file)
        ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # simple progress animation
    i=0
    while process.poll() is None:
        i=min(i+2,99)
        print(f"\rProgress: {i}%", end="")
        subprocess.run(["sleep","0.05"])

    process.wait()

    if out_file.exists():
        size_after = out_file.stat().st_size / (1024 * 1024)
    else:
        size_after = size_before

    print("\nDone..")
    print(f"Before: {size_before:.2f} MB")
    print(f"After:  {size_after:.2f} MB")

# =========================
# ADD NOTES
# =========================
def add_notes_task():
    p=clean_path(input("Path: "))
    n=int(input("Notes: "))

    song=load_json_minimal(p) or {"notes":[]}
    if not song["notes"]:
        song["notes"].append({"sectionNotes":[]})

    song["notes"][0].setdefault("sectionNotes",[]).extend([[0,0,0]]*n)

    with p.open("w",encoding="utf-8") as f:
        json.dump({"song":song},f,separators=(",",":"))

    print("Added")

# =========================
# REMOVE NOTES
# =========================
def remove_notes_task():
    p=clean_path(input("Path: "))
    n=int(input("Remove: "))

    song=load_json_minimal(p)
    if not song: return

    removed=0
    for sec in reversed(song.get("notes",[])):
        notes=get_notes(sec)
        while notes and removed<n:
            notes.pop(); removed+=1

    with p.open("w",encoding="utf-8") as f:
        json.dump({"song":song},f,separators=(",",":"))

    print(f"Removed {removed}")

# =========================
# SPLIT
# =========================
def split_task(path:Path,n:int):
    song=load_json_minimal(path)
    if not song: return

    secs=song.get("notes",[])
    chunk=math.ceil(len(secs)/n)

    for i in range(n):
        sub=secs[i*chunk:(i+1)*chunk]

        def gen():
            for s in sub: yield s

        write_stream(path.parent/f"{path.stem}_part{i+1}.json",song,gen(),len(sub))

# =========================
# MENU
# =========================
def main():
    while True:
        print(c("\n[ FAST FNF TOOL + MEDIA ]",Color.MAGENTA))
        print("1 Merge")
        print("2 Multiply")
        print("3 Split")
        print("4 Compress JSON")
        print("5 Add Notes")
        print("6 Remove Notes")
        print("7 Count Notes")
        print("8 Compress Video/Audio")
        print("Q Quit")

        ch=input("> ").upper().strip()
        if ch=="Q": break

        if ch=="1":
            raw=input("Paths: ")
            merge_task([clean_path(x) for x in shlex.split(raw)])
        elif ch=="2":
            multiply_task(clean_path(input("Path: ")),int(input("Mult: ")))
        elif ch=="3":
            split_task(clean_path(input("Path: ")),int(input("Parts: ")))
        elif ch=="4":
            compress_task(clean_path(input("Path: ")))
        elif ch=="5":
            add_notes_task()
        elif ch=="6":
            remove_notes_task()
        elif ch=="7":
            count_notes_task(clean_path(input("Path: ")))
        elif ch=="8":
            compress_media_task(clean_path(input("File Path: ")))

if __name__=="__main__":
    main()

import json
import os

json_path = input("Enter chart JSON path:\n> ").strip()

if not os.path.exists(json_path):
    print("File not found.")
    exit()

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

bf = input("Boyfriend path: ").strip()
gf = input("Girlfriend path: ").strip()
dad = input("Opponent path: ").strip()
stage = input("Stage path: ").strip()

# Change song section
song = data.get("song", data)

if bf:
    song["player1"] = bf

if dad:
    song["player2"] = dad

if gf:
    song["gfVersion"] = gf

if stage:
    song["stage"] = stage

with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)

print("\nChanging... Done!")

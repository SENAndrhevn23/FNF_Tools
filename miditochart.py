#!/usr/bin/env python3
import mido
import json
import os
import bisect
import time

# =========================
# CONFIG (SAFE DEFAULTS)
# =========================
SECTION_SIZE = 16
START_CUTOFF_MS = 250
REBASE_TO_ZERO = True

# =========================
# TEMPO UTILS (LOW MEMORY)
# =========================
def build_tempo_lookup(mid):
    tpq = mid.ticks_per_beat
    ticks = [0]
    ms = [0.0]
    tempos = [500000]

    for track in mid.tracks:
        t = 0
        for msg in track:
            t += msg.time
            if msg.type == "set_tempo":
                last_tick = ticks[-1]
                last_ms = ms[-1]
                last_tempo = tempos[-1]
                ms.append(last_ms + (t - last_tick) * last_tempo / tpq / 1000)
                ticks.append(t)
                tempos.append(msg.tempo)

    return ticks, ms, tempos, tpq

def tick_to_ms(tick, ticks, ms, tempos, tpq):
    i = bisect.bisect_right(ticks, tick) - 1
    return ms[i] + (tick - ticks[i]) * tempos[i] / tpq / 1000

# =========================
# MODE 1 — SPLIT MIDI (LOW RAM)
# =========================
def split_midi(midi_path, splits):
    mid = mido.MidiFile(midi_path, clip=True)

    # Calculate total ticks
    total_ticks = max(sum(msg.time for msg in track) for track in mid.tracks)
    part_len = total_ticks // splits

    name = os.path.splitext(os.path.basename(midi_path))[0]
    out_dir = f"{name}_MIDI_Splits"
    os.makedirs(out_dir, exist_ok=True)

    print("Splitting…")

    for i in range(splits):
        start = i * part_len
        end = total_ticks if i == splits - 1 else (i + 1) * part_len

        new_mid = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)

        for track in mid.tracks:
            new_track = mido.MidiTrack()
            new_mid.tracks.append(new_track)

            last_time = 0
            abs_t = 0
            for msg in track:
                abs_t += msg.time
                if start <= abs_t < end:
                    new_track.append(msg.copy(time=abs_t - start - last_time))
                    last_time = abs_t - start

        out_file = os.path.join(out_dir, f"part{i+1}.mid")
        new_mid.save(out_file)
        print(f"Saved {out_file}")

    print("Done splitting.")

# =========================
# MODE 2 — MIDI → CHART (LOW RAM)
# =========================
def midi_to_chart(midi_path, bpm, speed, side):
    mid = mido.MidiFile(midi_path, clip=True)
    ticks, ms, tempos, tpq = build_tempo_lookup(mid)

    must_hit = side == "player"
    name = os.path.splitext(os.path.basename(midi_path))[0]
    out_file = f"{name}_{side}.json"

    # Find first valid note
    first_note_ms = None
    for track in mid.tracks:
        abs_t = 0
        for msg in track:
            abs_t += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                m = tick_to_ms(abs_t, ticks, ms, tempos, tpq)
                if m >= START_CUTOFF_MS:
                    first_note_ms = m
                    break
        if first_note_ms is not None:
            break

    if first_note_ms is None:
        print("❌ No valid notes found")
        return

    notes_written = 0
    start_time = time.time()
    first_section = True

    with open(out_file, "w", encoding="utf-8") as f:
        f.write('{"song":{')
        f.write(f'"song":"{name}","notes":[')

        section = []

        for track in mid.tracks:
            abs_t = 0
            for msg in track:
                abs_t += msg.time
                if msg.type != "note_on" or msg.velocity <= 0:
                    continue

                m = tick_to_ms(abs_t, ticks, ms, tempos, tpq)
                if m < START_CUTOFF_MS:
                    continue
                if REBASE_TO_ZERO:
                    m -= first_note_ms

                lane = msg.note % 4
                section.append([int(m), lane, 0])
                notes_written += 1

                if len(section) == SECTION_SIZE:
                    if not first_section:
                        f.write(",")
                    f.write(json.dumps({
                        "sectionNotes": section,
                        "mustHitSection": must_hit,
                        "bpm": bpm,
                        "changeBPM": False,
                        "altAnim": False,
                        "gfSection": False,
                        "typeOfSection": 0
                    }))
                    section = []
                    first_section = False

        if section:
            if not first_section:
                f.write(",")
            f.write(json.dumps({
                "sectionNotes": section,
                "mustHitSection": must_hit,
                "bpm": bpm,
                "changeBPM": False,
                "altAnim": False,
                "gfSection": False,
                "typeOfSection": 0
            }))

        f.write(f'], "bpm":{bpm},"needsVoices":true,"speed":{speed},')
        f.write('"player1":"bf","player2":"dad","gfVersion":"gf","stage":"stage","events":[]}}')

    size_mb = os.path.getsize(out_file) / (1024 * 1024)
    total_duration = int((tick_to_ms(abs_t, ticks, ms, tempos, tpq)) / 1000)
    nps = notes_written / max(1, total_duration)

    print("\nChart Details\n")
    print(f"Notes: {notes_written:,}")
    print(f"Size: {size_mb:.1f}MB")
    print(f"Speed: {speed}")
    print(f"NPS: {int(nps):,}")
    print(f"Time: 0:{total_duration:.1f}")

# =========================
# START MENU
# =========================
def main():
    print("\n1 = Split MIDI only")
    print("2 = MIDI → Psych Chart")
    c = input("> ").strip()

    if c == "1":
        path = input("Enter MIDI Path: ").strip()
        splits = int(input("How many splits: ").strip())
        split_midi(path, splits)

    elif c == "2":
        print("3 = Opponent | 4 = Player")
        side = "player" if input("> ").strip() == "4" else "opponent"
        path = input("Enter MIDI Path: ").strip()
        bpm = float(input("Enter BPM: ").strip())
        speed = float(input("Enter Speed: ").strip())
        midi_to_chart(path, bpm, speed, side)

if __name__ == "__main__":
    main()

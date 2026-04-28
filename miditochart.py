#!/usr/bin/env python3
import mido
import json
import os
import bisect
from collections import defaultdict

# =========================
# CONFIG
# =========================
SECTION_BEATS = 4
START_CUTOFF_MS = 250
REBASE_TO_ZERO = True
MIN_VELOCITY = 1

# =========================
# TEMPO UTILS
# =========================
def build_tempo_lookup(mid):
    merged = mido.merge_tracks(mid.tracks)
    tpq = mid.ticks_per_beat

    # Keep tempo changes in absolute tick order
    tempo_events = [(0, 500000)]  # default MIDI tempo = 120 BPM

    abs_tick = 0
    for msg in merged:
        abs_tick += msg.time
        if msg.type == "set_tempo":
            if abs_tick == 0:
                tempo_events[0] = (0, msg.tempo)
            else:
                tempo_events.append((abs_tick, msg.tempo))

    tempo_events.sort(key=lambda x: x[0])

    ticks = []
    ms = []
    tempos = []

    cur_ms = 0.0
    prev_tick, prev_tempo = tempo_events[0]
    ticks.append(prev_tick)
    ms.append(cur_ms)
    tempos.append(prev_tempo)

    for tick, tempo in tempo_events[1:]:
        cur_ms += (tick - prev_tick) * prev_tempo / tpq / 1000.0
        ticks.append(tick)
        ms.append(cur_ms)
        tempos.append(tempo)
        prev_tick = tick
        prev_tempo = tempo

    return ticks, ms, tempos, tpq

def tick_to_ms(tick, ticks, ms, tempos, tpq):
    i = bisect.bisect_right(ticks, tick) - 1
    if i < 0:
        i = 0
    return ms[i] + (tick - ticks[i]) * tempos[i] / tpq / 1000.0

# =========================
# NOTE EXTRACTION
# =========================
def extract_notes(mid):
    merged = mido.merge_tracks(mid.tracks)
    abs_tick = 0

    # allow overlapping notes per channel+pitch
    active = defaultdict(list)
    notes = []

    for msg in merged:
        abs_tick += msg.time

        is_note_on = msg.type == "note_on" and msg.velocity > 0
        is_note_off = msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0)

        if is_note_on:
            active[(msg.channel, msg.note)].append((abs_tick, msg.velocity))

        elif is_note_off:
            key = (msg.channel, msg.note)
            if active[key]:
                start_tick, velocity = active[key].pop()
                if abs_tick > start_tick:
                    notes.append({
                        "note": msg.note,
                        "channel": msg.channel,
                        "velocity": velocity,
                        "start_tick": start_tick,
                        "end_tick": abs_tick
                    })

    notes.sort(key=lambda n: (n["start_tick"], n["note"], n["channel"]))
    return notes

# =========================
# PITCH -> LANE MAPPING
# =========================
def build_pitch_lane_map(notes):
    unique_pitches = sorted({n["note"] for n in notes})
    if not unique_pitches:
        return {}

    if len(unique_pitches) == 1:
        return {unique_pitches[0]: 2}  # single pitch -> UP lane

    lane_map = {}
    denom = len(unique_pitches) - 1

    for i, pitch in enumerate(unique_pitches):
        # spread lowest -> highest across lanes 0..3
        lane = int(round(i * 3 / denom))
        lane_map[pitch] = max(0, min(3, lane))

    return lane_map

def choose_lane(target_lane, occupied):
    if target_lane not in occupied:
        return target_lane

    # deterministic nearest-free-lane search
    for dist in range(1, 4):
        left = target_lane - dist
        right = target_lane + dist

        if left >= 0 and left not in occupied:
            return left
        if right <= 3 and right not in occupied:
            return right

    return target_lane

# =========================
# MODE 1 — SPLIT MIDI
# =========================
def split_midi(midi_path, splits):
    mid = mido.MidiFile(midi_path, clip=True)

    total_ticks = max(sum(msg.time for msg in track) for track in mid.tracks)
    part_len = total_ticks // splits if splits > 0 else total_ticks

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
# MODE 2 — MIDI → PSYCH CHART
# =========================
def midi_to_chart(midi_path, bpm, speed, side):
    mid = mido.MidiFile(midi_path, clip=True)
    ticks, ms, tempos, tpq = build_tempo_lookup(mid)

    must_hit = side == "player"
    name = os.path.splitext(os.path.basename(midi_path))[0]
    out_file = f"{name}_{side}.json"

    raw_notes = extract_notes(mid)
    if not raw_notes:
        print("❌ No valid notes found")
        return

    lane_map = build_pitch_lane_map(raw_notes)

    # Convert ticks -> ms first
    notes = []
    for n in raw_notes:
        start_ms = tick_to_ms(n["start_tick"], ticks, ms, tempos, tpq)
        end_ms = tick_to_ms(n["end_tick"], ticks, ms, tempos, tpq)

        if start_ms < START_CUTOFF_MS:
            continue

        notes.append({
            **n,
            "start_ms": start_ms,
            "end_ms": end_ms
        })

    if not notes:
        print("❌ No notes after cutoff")
        return

    # Rebase song to start at 0 if requested
    first_note_ms = min(n["start_ms"] for n in notes)
    if REBASE_TO_ZERO:
        for n in notes:
            n["start_ms"] -= first_note_ms
            n["end_ms"] -= first_note_ms

    # Group by exact original start tick so simultaneous notes stay together
    notes.sort(key=lambda n: (n["start_tick"], n["note"], n["channel"]))

    section_ms = (60000.0 / bpm) * SECTION_BEATS if bpm > 0 else 2000.0
    section_map = defaultdict(list)

    i = 0
    while i < len(notes):
        j = i
        start_tick = notes[i]["start_tick"]
        same_time = []

        while j < len(notes) and notes[j]["start_tick"] == start_tick:
            same_time.append(notes[j])
            j += 1

        occupied = set()

        # lower pitches first for chord readability
        same_time.sort(key=lambda n: (n["note"], n["channel"]))

        for n in same_time:
            target_lane = lane_map.get(n["note"], 2)
            lane = choose_lane(target_lane, occupied)
            occupied.add(lane)

            strum_time = int(round(n["start_ms"]))
            sustain = max(0, int(round(n["end_ms"] - n["start_ms"])))

            section_idx = int(strum_time // section_ms) if section_ms > 0 else 0
            section_map[section_idx].append([strum_time, lane, sustain])

        i = j

    max_section = max(section_map.keys()) if section_map else 0
    sections = []

    for idx in range(max_section + 1):
        sections.append({
            "sectionNotes": section_map.get(idx, []),
            "mustHitSection": must_hit,
            "bpm": bpm,
            "changeBPM": False,
            "altAnim": False,
            "gfSection": False,
            "typeOfSection": 0,
            "lengthInSteps": 16
        })

    chart = {
        "song": {
            "song": name,
            "notes": sections,
            "bpm": bpm,
            "needsVoices": True,
            "speed": speed,
            "player1": "bf",
            "player2": "dad",
            "gfVersion": "gf",
            "stage": "stage",
            "events": []
        }
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(chart, f, indent=2)

    size_mb = os.path.getsize(out_file) / (1024 * 1024)
    total_duration_sec = max(1, int(round(max(n["end_ms"] for n in notes) / 1000.0)))
    nps = len(notes) / max(1, total_duration_sec)

    print("\nChart Details\n")
    print(f"Notes: {len(notes):,}")
    print(f"Size: {size_mb:.1f}MB")
    print(f"Speed: {speed}")
    print(f"NPS: {int(nps):,}")
    print(f"Time: 0:{total_duration_sec:.1f}")
    print(f"Saved: {out_file}")

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

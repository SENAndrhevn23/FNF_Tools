import mido
import json
import os

def menu():
    print("\nTurn Midis To Psych Engine Charts (Full song on one side)\n")
    print("1: Midi To FNF Chart (fnfc file) [coming soon]")
    print("3: Full song → Opponent side only (left arrows)")
    print("4: Full song → Player side only (right arrows)\n")
    return input("> ").strip()

def ticks_to_ms(ticks, ticks_per_beat, tempo_map):
    """Convert absolute ticks to milliseconds using tempo map"""
    ms = 0
    last_tick = 0
    last_tempo = 500000  # default
    for t_tick, t_tempo in tempo_map:
        if ticks < t_tick:
            ms += (ticks - last_tick) * last_tempo / ticks_per_beat / 1000
            return ms
        ms += (t_tick - last_tick) * last_tempo / ticks_per_beat / 1000
        last_tick = t_tick
        last_tempo = t_tempo
    # Remaining ticks after last tempo change
    ms += (ticks - last_tick) * last_tempo / ticks_per_beat / 1000
    return ms

def midi_to_psych_json(midi_path, bpm, song_name="Test", target_side="player"):
    if not os.path.exists(midi_path):
        print("❌ Midi file not found.")
        return

    try:
        mid = mido.MidiFile(midi_path)
    except Exception as e:
        print(f"❌ Failed to load MIDI: {e}")
        return

    ticks_per_beat = mid.ticks_per_beat
    print(f"Ticks per beat: {ticks_per_beat}")

    # ───────────────────────────────────────────────
    # Step 1: Build tempo map (tick → tempo)
    # ───────────────────────────────────────────────
    tempo_map = [(0, 500000)]  # default tempo
    abs_ticks = 0
    for track in mid.tracks:
        tick_acc = 0
        for msg in track:
            tick_acc += msg.time
            if msg.type == 'set_tempo':
                tempo_map.append((tick_acc, msg.tempo))

    tempo_map.sort(key=lambda x: x[0])

    # ───────────────────────────────────────────────
    # Step 2: Flatten all note_on events
    # ───────────────────────────────────────────────
    events = []
    for track in mid.tracks:
        tick_acc = 0
        for msg in track:
            tick_acc += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                events.append((tick_acc, msg.note))

    if not events:
        print("❌ No notes found in MIDI.")
        return

    # Sort by absolute tick
    events.sort(key=lambda x: x[0])

    # ───────────────────────────────────────────────
    # Step 3: Convert ticks → ms accurately
    # ───────────────────────────────────────────────
    notes = []
    for abs_tick, note_num in events:
        ms = ticks_to_ms(abs_tick, ticks_per_beat, tempo_map)
        lane = note_num % 8
        notes.append({'time_ms': ms, 'original_lane': lane})

    # ───────────────────────────────────────────────
    # Step 4: Remap lanes 0-3
    # ───────────────────────────────────────────────
    remapped_notes = []
    for n in notes:
        new_lane = n['original_lane'] % 4
        remapped_notes.append({
            'time_ms': n['time_ms'],
            'lane': new_lane,
            'length_ms': 0
        })

    # ───────────────────────────────────────────────
    # Step 5: Build sections
    # ───────────────────────────────────────────────
    max_notes_per_section = 16
    sections = []
    current_notes = []
    must_hit = target_side == "player"

    for note in remapped_notes:
        current_notes.append([
            int(note['time_ms']),
            note['lane'],
            note['length_ms']
        ])
        if len(current_notes) >= max_notes_per_section:
            sections.append({
                "sectionNotes": current_notes[:],
                "mustHitSection": must_hit,
                "bpm": bpm,
                "changeBPM": False,
                "altAnim": False,
                "gfSection": False,
                "typeOfSection": 0
            })
            current_notes = []

    if current_notes:
        sections.append({
            "sectionNotes": current_notes,
            "mustHitSection": must_hit,
            "bpm": bpm,
            "changeBPM": False,
            "altAnim": False,
            "gfSection": False,
            "typeOfSection": 0
        })

    # ───────────────────────────────────────────────
    # Step 6: Save JSON
    # ───────────────────────────────────────────────
    chart = {
        "song": {
            "song": song_name,
            "notes": sections,
            "bpm": bpm,
            "needsVoices": True,
            "speed": 1.0,
            "player1": "bf",
            "player2": "dad",
            "gfVersion": "gf",
            "stage": "stage",
            "events": []
        }
    }

    suffix = "player_full" if target_side == "player" else "opponent_full"
    out_path = f"{os.path.splitext(os.path.basename(midi_path))[0]}_{suffix}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chart, f, indent=2)

    print(f"\nDone! Saved: {out_path}")
    print(f"Total notes: {sum(len(s['sectionNotes']) for s in sections)}")

def main():
    choice = menu()
    if choice == "1":
        print("\nComing soon 👀")
        return
    if choice not in ["3", "4"]:
        print("Please choose 3 or 4.")
        return

    path = input("\nEnter Midi Path: ").strip()
    try:
        bpm = float(input("Enter BPM: ").strip())
    except:
        print("Bad BPM → using 120")
        bpm = 120

    name = input("Song Name [optional]: ").strip() or "Test"
    side = "player" if choice == "4" else "opponent"
    midi_to_psych_json(path, bpm, name, target_side=side)

if __name__ == "__main__":
    main()
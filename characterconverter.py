import json
import os
import xml.etree.ElementTree as ET
import re
import xml.dom.minidom

def print_header():
    print("\n" + "=" * 30)
    print("      FNF ASSET CONVERTER     ")
    print("=" * 30)

def main_menu():
    while True:
        print_header()
        print("1: Character Converter")
        print("2: Noteskin Converter")
        print("3: Exit")
        choice = input("\nSelect an option (1-3): ").strip()

        if choice == "1":
            run_character_converter()
        elif choice == "2":
            run_noteskin_converter()
        elif choice == "3":
            print("Exiting tool... Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1, 2, or 3.")

# ==========================================
# 1. CHARACTER CONVERTER (FIXED KEYWORDS)
# ==========================================
def run_character_converter():
    print("\n--- Character Converter ---")
    png_path = input("Enter PNG Path: ").strip()
    xml_path = input("Enter XML Path: ").strip()

    prefix_to_replace = input("Enter prefix to replace (e.g., BF, BOYFRIEND) [Leave blank to skip]: ").strip().upper()
    new_name = input("Enter new character name: ").strip()

    if not os.path.exists(xml_path):
        print(f"Error: XML file not found at {xml_path}")
        return

    print("Creating Json...")
    print("It may take a few minutes or seconds")

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        unique_anim_names = set()
        for subtexture in root.findall("SubTexture"):
            name_attr = subtexture.get("name")
            if name_attr:
                base_name = re.sub(r"\d+$", "", name_attr).strip()
                if base_name:
                    unique_anim_names.add(base_name)

        animations_list = []

        for xml_name in sorted(unique_anim_names):
            upper_xml = xml_name.upper()
            anim_key = xml_name

            # Dynamic keyword check
            if "MISS" in upper_xml:
                if "LEFT" in upper_xml: anim_key = "singLEFTmiss"
                elif "DOWN" in upper_xml: anim_key = "singDOWNmiss"
                elif "UP" in upper_xml: anim_key = "singUPmiss"
                elif "RIGHT" in upper_xml: anim_key = "singRIGHTmiss"
            elif "NOTE" in upper_xml or "SING" in upper_xml:
                if "LEFT" in upper_xml: anim_key = "singLEFT"
                elif "DOWN" in upper_xml: anim_key = "singDOWN"
                elif "UP" in upper_xml: anim_key = "singUP"
                elif "RIGHT" in upper_xml: anim_key = "singRIGHT"
            elif "IDLE" in upper_xml or "DANCE" in upper_xml:
                anim_key = "idle"
            elif "HEY" in upper_xml or "CHEER" in upper_xml:
                anim_key = "hey"
            elif "HIT" in upper_xml or "HURT" in upper_xml:
                anim_key = "hurt"
            elif "SCARED" in upper_xml or "SHAKING" in upper_xml:
                anim_key = "scared"
            elif "DODGE" in upper_xml:
                anim_key = "dodge"
            elif "ATTACK" in upper_xml and "PRE" not in upper_xml:
                anim_key = "attack"
            elif "PRE ATTACK" in upper_xml or "PRE-ATTACK" in upper_xml:
                anim_key = "pre-attack"

            final_xml_name = xml_name
            if prefix_to_replace and new_name:
                pattern = re.compile(re.escape(prefix_to_replace), re.IGNORECASE)
                final_xml_name = pattern.sub(new_name, xml_name)

            offsets = [0, 0]
            if anim_key == "idle": offsets = [-5, 0]
            elif anim_key == "singLEFT": offsets = [5, -6]
            elif anim_key == "singDOWN": offsets = [-20, -51]
            elif anim_key == "singUP": offsets = [-46, 27]
            elif anim_key == "singRIGHT": offsets = [-48, -7]

            loop = True if "scared" in anim_key or "idle" in anim_key else False

            animations_list.append({
                "offsets": offsets,
                "loop": loop,
                "fps": 24,
                "anim": anim_key,
                "indices": [],
                "name": final_xml_name,
            })

        base_file_name = os.path.splitext(os.path.basename(png_path))[0]
        json_data = {
            "animations": animations_list,
            "no_antialiasing": False,
            "image": f"characters/{base_file_name}",
            "position": [0, 350],
            "healthicon": base_file_name.lower(),
            "flip_x": True,
            "healthbar_colors": [49, 176, 209],
            "camera_position": [0, 0],
            "sing_duration": 4,
            "scale": 1,
        }

        output_json_path = os.path.splitext(xml_path)[0] + ".json"
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4)

        print("Done.")
        print(f"Saved file to: {output_json_path}")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

# ==========================================
# 2. NOTESKIN CONVERTER
# ==========================================
def run_noteskin_converter():
    print("\n--- Noteskin Converter ---")
    png_path = input("Enter PNG Path: ").strip()

    if not png_path or not os.path.exists(png_path):
        print("Error: Valid PNG image asset path required.")
        return

    print("Converting..")
    print("Making XML..")

    try:
        # Standard names for layout atlas mapping
        note_names = [
            "arrowLEFT0000", "arrowDOWN0000", "arrowRIGHT0000", "arrowUP0000",
            "blue0000", "green0000", "purple0000", "red0000",
            "blue hold piece0000", "blue hold end0000",
            "green hold piece0000", "green hold end0000",
            "purple hold piece0000", "pruple end hold0000",
            "red hold piece0000", "red hold end0000",
            "left press0000", "down press0000", "up press0000", "right press0000",
            "left confirm0000", "down confirm0000", "up confirm0000", "right confirm0000"
        ]

        filename = os.path.basename(png_path)
        
        # Build TextureAtlas XML Structure
        root = ET.Element("TextureAtlas", imagePath=filename)
        root.append(ET.Comment(" Generated automatically via FNF Conversion Tool "))

        # Distribute assets into an automated simple layout matrix tracking position coordinates
        # Assumed standard block boundary dimensions for dynamic notes skin grids
        box_w, box_h = 155, 153 
        columns = 4

        for index, name in enumerate(note_names):
            col = index % columns
            row = index // columns
            
            x_pos = 2 + (col * (box_w + 5))
            y_pos = 45 + (row * (box_h + 5))

            # Shrink tracking cuts tailored for thin hold tail segments 
            if "piece" in name or "end" in name or "hold" in name:
                width, height = 50, 64
            else:
                width, height = box_w, box_h

            sub_texture = ET.SubElement(root, "SubTexture")
            sub_texture.set("name", name)
            sub_texture.set("x", str(x_pos))
            sub_texture.set("y", str(y_pos))
            sub_texture.set("width", str(width))
            sub_texture.set("height", str(height))

        # Pretty print writing out the formatting
        xml_string = ET.tostring(root, encoding="utf-8")
        parsed_xml = xml.dom.minidom.parseString(xml_string)
        pretty_xml = parsed_xml.toprettyxml(indent="\t", encoding="utf-8")

        output_xml_path = os.path.splitext(png_path)[0] + ".xml"
        with open(output_xml_path, "wb") as f:
            f.write(pretty_xml)

        print("Done.")
        print(f"Saved XML to: {output_xml_path}")

    except Exception as e:
        print(f"\nAn error occurred while generating the XML template layout: {e}")

if __name__ == "__main__":
    main_menu()

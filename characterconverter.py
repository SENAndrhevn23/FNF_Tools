import json
import os
import re
import xml.etree.ElementTree as ET


def generate_fnf_json():
    # 1. Gather inputs
    png_path = input("Enter PNG Path: ").strip()
    xml_path = input("Enter XML Path: ").strip()

    # New inputs for custom name swapping
    prefix_to_replace = (
        input("Enter prefix to replace (e.g., BF, BOYFRIEND) [Leave blank to skip]: ")
        .strip()
        .upper()
    )
    new_name = input("Enter new character name: ").strip()

    if not os.path.exists(xml_path):
        print(f"Error: XML file not found at {xml_path}")
        return

    print("Creating Json...")
    print("It may take a few minutes or seconds")

    try:
        # 2. Parse XML to extract animation names
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # We'll use a set to keep track of unique base animation names
        unique_anim_names = set()

        for subtexture in root.findall("SubTexture"):
            name_attr = subtexture.get("name")
            if name_attr:
                # Remove trailing frame numbers (e.g., "BF HEY0025" -> "BF HEY")
                base_name = re.sub(r"\d+$", "", name_attr).strip()
                if base_name:
                    unique_anim_names.add(base_name)

        # 3. Standard game animation keys mapping based on standard prefixes
        name_mapping = {
            "BF idle dance": "idle",
            "BOYFRIEND idle dance": "idle",
            "BF NOTE LEFT0": "singLEFT",
            "BOYFRIEND NOTE LEFT0": "singLEFT",
            "BF NOTE DOWN0": "singDOWN",
            "BOYFRIEND NOTE DOWN0": "singDOWN",
            "BF NOTE UP0": "singUP",
            "BOYFRIEND NOTE UP0": "singUP",
            "BF NOTE RIGHT0": "singRIGHT",
            "BOYFRIEND NOTE RIGHT0": "singRIGHT",
            "BF NOTE LEFT MISS": "singLEFTmiss",
            "BOYFRIEND NOTE LEFT MISS": "singLEFTmiss",
            "BF NOTE DOWN MISS": "singDOWNmiss",
            "BOYFRIEND NOTE DOWN MISS": "singDOWNmiss",
            "BF NOTE UP MISS": "singUPmiss",
            "BOYFRIEND NOTE UP MISS": "singUPmiss",
            "BF NOTE RIGHT MISS": "singRIGHTmiss",
            "BOYFRIEND NOTE RIGHT MISS": "singRIGHTmiss",
            "BF HEY": "hey",
            "BOYFRIEND HEY": "hey",
            "BF hit": "hurt",
            "BOYFRIEND hit": "hurt",
            "BF idle shaking": "scared",
            "BOYFRIEND idle shaking": "scared",
            "boyfriend dodge": "dodge",
            "boyfriend attack": "attack",
            "bf pre attack": "pre-attack",
        }

        animations_list = []

        # 4. Generate animation entry configs
        for xml_name in sorted(unique_anim_names):
            # Figure out the proper in-game key (e.g., singLEFT) before we change the name string
            anim_key = name_mapping.get(xml_name, xml_name)

            # --- Name Replacement Step ---
            final_xml_name = xml_name
            if prefix_to_replace and new_name:
                # Uses regex to replace the prefix safely, even if case differs
                pattern = re.compile(re.escape(prefix_to_replace), re.IGNORECASE)
                final_xml_name = pattern.sub(new_name, xml_name)
            # -----------------------------

            # Assign default offsets (0,0) to be tweaked later in Psych Engine's editor
            offsets = [0, 0]

            # Hardcoded helper offsets mapping based on your example character layout
            if anim_key == "idle":
                offsets = [-5, 0]
            elif anim_key == "singLEFT":
                offsets = [5, -6]
            elif anim_key == "singDOWN":
                offsets = [-20, -51]
            elif anim_key == "singUP":
                offsets = [-46, 27]
            elif anim_key == "singRIGHT":
                offsets = [-48, -7]

            # Determine loop properties
            loop = True if "shaking" in xml_name.lower() or "idle" in xml_name.lower() else False

            anim_entry = {
                "offsets": offsets,
                "loop": loop,
                "fps": 24,
                "anim": anim_key,
                "indices": [],
                "name": final_xml_name,  # Uses the newly renamed prefix
            }
            animations_list.append(anim_entry)

        # Extract filename without extension for asset path configs
        base_file_name = os.path.splitext(os.path.basename(png_path))[0]

        # 5. Build full JSON template structure
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

        # 6. Save the output JSON file
        output_json_path = os.path.splitext(xml_path)[0] + ".json"
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=4)

        print("Done.")
        print(f"Saved file to: {output_json_path}")

    except Exception as e:
        print(f"\nAn error occurred while generating the JSON: {e}")


if __name__ == "__main__":
    generate_fnf_json()

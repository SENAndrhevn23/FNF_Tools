import json
import os


def print_header():
    print("\n" + "=" * 30)
    print("      FNF MULTI-TOOL       ")
    print("=" * 30)


def main_menu():
    while True:
        print_header()
        print("1: Stage Converter")
        print("2: Shader Converter")
        print("3: Exit")
        choice = input("\nSelect an option (1-3): ").strip()

        if choice == "1":
            run_stage_converter()
        elif choice == "2":
            run_shader_converter()
        elif choice == "3":
            print("Exiting... Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1, 2, or 3.")


# ==========================================
# 1. STAGE CONVERTER METHOD
# ==========================================
def run_stage_converter():
    print("\n--- Stage Converter ---")
    png_path = input("Enter PNG Path: ").strip()

    if not png_path:
        print("Error: PNG path cannot be empty.")
        return

    print("Creating Json...")
    print("It may take a few minutes or seconds")

    # Extract base name (e.g., 'AUGBACKGROUND' from 'assets/AUGBACKGROUND.png')
    base_name = os.path.splitext(os.path.basename(png_path))[0]
    directory = os.path.dirname(png_path)

    # 1. Generate stage.json config template
    stage_json_data = {
        "directory": "week1",
        "defaultZoom": 0.9,
        "stageUI": "",
        "boyfriend": [770, 100],
        "girlfriend": [400, 130],
        "opponent": [100, 100],
        "hide_girlfriend": False,
        "camera_boyfriend": [-150, 0],
        "camera_opponent": [50, 0],
        "camera_girlfriend": [0, 0],
        "camera_speed": 1,
        "preload": {
            f"images/{base_name}": 3,
            "images/stagefront": 3,
            "images/spotlight": 3,
            "images/smoke": 3,
            "images/stagecurtains": 2,
            "images/stage_light": 2,
        },
        "_editorMeta": {"dad": "dad", "boyfriend": "bf", "gf": "gf"},
    }

    # Save JSON file
    json_out_path = os.path.join(directory, f"{base_name.lower()}.json")
    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(stage_json_data, f, indent=4)

    # 2. Generate stage.lua asset script
    lua_content = f"""function onCreate()
    makeLuaSprite('stage', '{base_name}', -880, -500)
    scaleObject('stage', 1.15, 1.15);
    addLuaSprite('stage', false)
end
"""

    lua_out_path = os.path.join(directory, f"{base_name.lower()}.lua")
    with open(lua_out_path, "w", encoding="utf-8") as f:
        f.write(lua_content)

    print("Done.")
    print(f"Generated: {json_out_path}")
    print(f"Generated: {lua_out_path}")


# ==========================================
# 2. SHADER CONVERTER METHOD
# ==========================================
def run_shader_converter():
    print("\n--- Shader Converter ---")
    frag_path = input("Enter Shader Frag File Path: ").strip()
    shader_name = input("Enter Name: ").strip()

    if not frag_path or not shader_name:
        print("Error: Path and Name cannot be empty.")
        return

    print("Converting..")
    print("Making Json..")
    print("Making Lua..")

    directory = os.path.dirname(frag_path)

    # 1. Generate shader json layout configurations
    shader_json_data = {
        "directory": "",
        "defaultZoom": 0.7,
        "isPixelStage": False,
        "hide_girlfriend": True,
        "boyfriend": [0, 300],
        "girlfriend": [0, 130],
        "opponent": [-800, 100],
    }

    # Save JSON configuration output
    json_out_path = os.path.join(directory, f"{shader_name.lower()}.json")
    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(shader_json_data, f, indent=4)

    # 2. Generate script template parsing shader configuration floats
    lua_content = f"""function onCreate()
	makeAnimatedLuaSprite('bg', 'moribund3purp', 220, -150);
	setScrollFactor('bg', 0.9, 0.9);
	scaleObject('bg', 192, 192)
	setProperty('bg.alpha', 1)
	addLuaSprite('bg', false);
	
	initLuaShader("{shader_name}")
	setSpriteShader("bg", "{shader_name}")

	makeLuaSprite('oppSprite', 'Netherite_Pickaxe_JE3', -800, 300);
	scaleObject('oppSprite', 2.5, 2.5);
	setScrollFactor('oppSprite', 1, 1);
	addLuaSprite('oppSprite', false);
	setProperty('healthGain', getProperty('healthGain') * 0.4)
end

function onUpdate(elapsed)
	setShaderFloat('bg', 'iTime', getSongPosition()/1000)
end
"""

    lua_out_path = os.path.join(directory, f"{shader_name.lower()}.lua")
    with open(lua_out_path, "w", encoding="utf-8") as f:
        f.write(lua_content)

    print("Done..")
    print(f"Generated: {json_out_path}")
    print(f"Generated: {lua_out_path}")


if __name__ == "__main__":
    main_menu()

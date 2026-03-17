import argparse
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from utils import find_suggestion

def verify_gamelists(esde_dir: str, roms_dir: str, auto_replace: bool):
    esde_path = Path(esde_dir).resolve()
    roms_path = Path(roms_dir).resolve()
    
    gamelists_dir = esde_path / "gamelists"

    if not esde_path.exists():
        print(f"❌ Error: ES-DE directory not found at '{esde_path}'")
        return

    if not gamelists_dir.exists():
        print(f"❌ Error: Gamelists directory not found at '{gamelists_dir}'")
        return

    if not roms_path.exists():
        print(f"❌ Error: ROMs directory not found at '{roms_path}'")
        return

    # Find all system folders inside the gamelists directory
    system_dirs = [d for d in gamelists_dir.iterdir() if d.is_dir() and not d.name.startswith("._")]
    
    if not system_dirs:
        print(f"⚠️ No system directories found in '{gamelists_dir}'.")
        return

    print(f"🔍 Searching for ROMs in: {roms_path}")
    print(f"📂 Scanning gamelists in {len(system_dirs)} system(s). Starting verification...\n")
    if auto_replace:
        print("⚠️  AUTO-REPLACE IS ON. XML files will be modified automatically.\n")
    print("-" * 50)

    total_missing = 0
    total_replaced = 0
    total_games = 0
    processed_gamelists = 0

    for system_dir in sorted(system_dirs):
        gamelist_xml = system_dir / "gamelist.xml"
        if not gamelist_xml.exists():
            continue

        system_name = system_dir.name
        system_rom_dir = roms_path / system_name
        
        print(f"📁 Verifying System: {system_name} ({gamelist_xml.name})")
        processed_gamelists += 1

        try:
            with open(gamelist_xml, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except UnicodeDecodeError:
            print(f"  ⚠️ Skipping {system_name}: Unable to read file (invalid encoding).")
            print("-" * 50)
            continue

        # ES-DE sometimes puts <alternativeEmulator> outside <gameList>
        # creating multiple XML roots. We bypass this by wrapping the inner content.
        xml_decl_match = re.match(r'^(<\?xml.*?\?>)\s*', raw_content, flags=re.IGNORECASE)
        if xml_decl_match:
            inner_content = raw_content[xml_decl_match.end():]
        else:
            inner_content = raw_content

        wrapped_content = f"<dummy_es_de_root>{inner_content}</dummy_es_de_root>"

        try:
            root = ET.fromstring(wrapped_content)
        except ET.ParseError as e:
            print(f"  ⚠️ Skipping {system_name}: Unable to parse gamelist.xml (invalid XML). Error: {e}")
            print("-" * 50)
            continue

        missing_in_gamelist = []
        modifications_made = 0
        system_games_count = 0

        # Use .//game to find games anywhere inside our dummy root
        for game in root.findall('.//game'):
            path_elem = game.find('path')
            if path_elem is None or not path_elem.text:
                continue
            
            system_games_count += 1
            total_games += 1
            
            original_path_str = path_elem.text.strip()
            
            # ES-DE gamelist paths typically start with './' indicating the system's ROM root
            if original_path_str.startswith("./"):
                relative_path = original_path_str[2:]
            else:
                relative_path = original_path_str

            actual_path = system_rom_dir / relative_path

            if not actual_path.exists():
                expected_dir = actual_path.parent
                suggestion = find_suggestion(actual_path, expected_dir)
                replaced = False

                if suggestion and auto_replace:
                    # Reconstruct the path keeping the ES-DE specific relative indicator
                    if '/' in original_path_str:
                        parent_dir = original_path_str.rsplit('/', 1)[0]
                        new_path_str = f"{parent_dir}/{suggestion}"
                    elif '\\' in original_path_str:
                        parent_dir = original_path_str.rsplit('\\', 1)[0]
                        new_path_str = f"{parent_dir}\\{suggestion}"
                    else:
                        new_path_str = suggestion

                    # Safely replace only this specific path in the raw text using a regex
                    pattern = rf"(<path>\s*){re.escape(original_path_str)}(\s*</path>)"
                    raw_content = re.sub(
                        pattern, 
                        lambda m, new_str=new_path_str: f"{m.group(1)}{new_str}{m.group(2)}", 
                        raw_content
                    )
                    
                    modifications_made += 1
                    total_replaced += 1
                    replaced = True
                
                missing_in_gamelist.append((original_path_str, suggestion, replaced))
                total_missing += 1

        # Output logic for the current gamelist
        if missing_in_gamelist:
            print(f"  ❌ Found {len(missing_in_gamelist)} missing ROM(s) out of {system_games_count}:")
            for original, suggestion, replaced in missing_in_gamelist:
                filename = Path(original).name
                display_path = filename if len(filename) < 60 else f"...{filename[-57:]}"
                
                if replaced:
                    print(f"    🔄 Replaced: {display_path} -> {suggestion}")
                else:
                    print(f"    - {display_path}")
                    if suggestion:
                        print(f"      💡 Suggestion: {suggestion}")
        else:
            if system_games_count == 0:
                print("  ⚠️ Gamelist contains no game entries.")
            else:
                print(f"  ✅ All {system_games_count} ROM(s) found.")

        # Write back raw changes directly (bypassing ET formatting destruction)
        if auto_replace and modifications_made > 0:
            with open(gamelist_xml, 'w', encoding='utf-8') as f:
                f.write(raw_content)
            print(f"  💾 Saved {modifications_made} replacements to {gamelist_xml.name}")
            
        print("-" * 50)

    print("\n📊 SUMMARY")
    print(f"Total Gamelists Checked: {processed_gamelists}")
    print(f"Total Games Processed: {total_games}")
    if total_missing > 0:
        print(f"Total Missing ROMs Found: {total_missing}")
        if auto_replace:
            print(f"Total ROMs Auto-Replaced: {total_replaced} 🔄")
            remaining = total_missing - total_replaced
            if remaining > 0:
                print(f"Remaining Missing ROMs (No suggestions found): {remaining} ❌")
            else:
                print("All missing ROMs were successfully replaced! ✅")
        else:
            print(f"Run with --replace to automatically apply suggestions.")
    else:
        print("All gamelists are perfectly in sync with your ROM files! ✅")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify ES-DE gamelist XMLs against your actual ROMs directory."
    )
    parser.add_argument(
        "--esde-dir", 
        required=True,
        type=str, 
        help="The path to your es-de configuration directory (containing gamelists/)"
    )
    parser.add_argument(
        "--roms-dir", 
        required=True,
        type=str, 
        help="The path to your actual ROMs directory"
    )
    parser.add_argument(
        "--replace", 
        action="store_true", 
        help="Automatically apply suggestions and modify the gamelist.xml files."
    )
    
    args = parser.parse_args()
    verify_gamelists(args.esde_dir, args.roms_dir, args.replace)
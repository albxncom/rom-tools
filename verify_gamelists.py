import argparse
import os
import re
import difflib
import xml.etree.ElementTree as ET
from pathlib import Path

def clean_title(filename: str) -> str:
    """
    Removes the file extension and anything inside () or [] brackets
    to get the clean base title for fuzzy matching.
    """
    name = Path(filename).stem
    clean = re.sub(r'\(.*?\)|\[.*?\]', '', name).strip()
    return clean

def find_suggestion(missing_file_path: Path, expected_dir: Path) -> str:
    """
    Looks in the expected directory for a file with a similar base name.
    """
    if not expected_dir.exists():
        return None
    
    # Get all valid files in the expected directory (ignore macOS hidden files)
    available_files = [f.name for f in expected_dir.iterdir() if f.is_file() and not f.name.startswith('._')]
    if not available_files:
        return None

    missing_clean = clean_title(missing_file_path.name)
    
    # Map cleaned available titles to their actual filenames
    clean_to_actual = {clean_title(f): f for f in available_files}
    
    # Find the closest match using difflib (0.6 cutoff means it needs to be 60% similar)
    matches = difflib.get_close_matches(missing_clean, clean_to_actual.keys(), n=1, cutoff=0.6)
    
    if matches:
        return clean_to_actual[matches[0]]
    return None

def verify_gamelists(root_dir: str, auto_replace: bool):
    root_path = Path(root_dir).resolve()
    gamelists_dir = root_path / "es-de" / "gamelists"
    roms_dir = root_path / "ROMs"

    if not root_path.exists():
        print(f"❌ Error: Root directory not found at '{root_path}'")
        return

    if not gamelists_dir.exists():
        print(f"❌ Error: Gamelists directory not found at '{gamelists_dir}'")
        return

    if not roms_dir.exists():
        print(f"❌ Error: ROMs directory not found at '{roms_dir}'")
        return

    # Find all system folders inside the gamelists directory
    system_dirs = [d for d in gamelists_dir.iterdir() if d.is_dir() and not d.name.startswith("._")]
    
    if not system_dirs:
        print(f"⚠️ No system directories found in '{gamelists_dir}'.")
        return

    print(f"🔍 Searching for ROMs in: {roms_dir}")
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
        system_rom_dir = roms_dir / system_name
        
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
                    # We use a lambda to avoid backslash escape issues in the replacement string
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
        "root_dir", 
        type=str, 
        help="The root path to your Ayaneo setup (e.g., /Volumes/SD/ayaneo)"
    )
    parser.add_argument(
        "--replace", 
        action="store_true", 
        help="Automatically apply suggestions and modify the gamelist.xml files."
    )
    
    args = parser.parse_args()
    verify_gamelists(args.root_dir, args.replace)
import argparse
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from utils import fuzzy_substring_match

def update_es_settings(esde_dir: Path, collection_name: str):
    """
    Safely injects the new collection name into es_settings.xml.
    ES-DE's settings file lacks a root element, so we parse it line-by-line.
    """
    settings_path = esde_dir / "settings" / "es_settings.xml"
    
    if not settings_path.exists():
        print(f"⚠️  es_settings.xml not found at '{settings_path}'. You will need to enable the collection manually in ES-DE.")
        return

    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"⚠️  Could not read es_settings.xml: {e}")
        return

    target_prefix = '<string name="CollectionSystemsCustom"'
    modified = False
    found_key = False

    for i, line in enumerate(lines):
        if line.strip().startswith(target_prefix):
            found_key = True
            # Extract the current comma-separated value
            match = re.search(r'value="([^"]*)"', line)
            if match:
                current_values = match.group(1).strip()
                if current_values:
                    collections = [c.strip() for c in current_values.split(',')]
                else:
                    collections = []

                # Add the new collection if it's not already there
                if collection_name not in collections:
                    collections.append(collection_name)
                    # Keep the list neatly alphabetized (case-insensitive)
                    collections.sort(key=str.lower)
                    new_values = ",".join(collections)
                    
                    # Reconstruct the line preserving indentation
                    indent = line[:len(line) - len(line.lstrip())]
                    lines[i] = f'{indent}<string name="CollectionSystemsCustom" value="{new_values}" />\n'
                    modified = True
                else:
                    print(f"ℹ️  Collection '{collection_name}' is already enabled in es_settings.xml.")
            break

    # If the key doesn't exist at all, we append it
    if not found_key:
        lines.append(f'<string name="CollectionSystemsCustom" value="{collection_name}" />\n')
        modified = True

    if modified:
        with open(settings_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"⚙️  Successfully activated '{collection_name}' in es_settings.xml!")

def create_collection(esde_dir: str, search_term: str, collection_name: str = None, cutoff: float = 0.80, auto_confirm: bool = False, use_regex: bool = False):
    esde_path = Path(esde_dir).resolve()
    gamelists_dir = esde_path / "gamelists"
    collections_dir = esde_path / "collections"

    if not esde_path.exists():
        print(f"❌ Error: ES-DE directory not found at '{esde_path}'")
        return
    if not gamelists_dir.exists():
        print(f"❌ Error: Gamelists directory not found at '{gamelists_dir}'")
        return

    # Ensure collections directory exists
    collections_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize and format the collection file name
    if not collection_name:
        clean_name = re.sub(r'[^A-Za-z0-9_\- ]+', '', search_term).strip()
        if not clean_name:
            clean_name = "Regex_Search" if use_regex else "Fuzzy_Search"
    else:
        clean_name = collection_name

    cfg_filename = f"custom-{clean_name}.cfg"
    cfg_output_path = collections_dir / cfg_filename

    system_dirs = [d for d in gamelists_dir.iterdir() if d.is_dir() and not d.name.startswith("._")]
    if not system_dirs:
        print(f"⚠️ No system directories found in '{gamelists_dir}'.")
        return

    regex_pattern = None
    if use_regex:
        try:
            # Compile regex once before looping, ignoring case for convenience
            regex_pattern = re.compile(search_term, re.IGNORECASE)
            print(f"🔍 Executing REGEX search for '{search_term}' across {len(system_dirs)} systems...")
        except re.error as e:
            print(f"❌ Error: Invalid regular expression '{search_term}'. Details: {e}")
            return
    else:
        print(f"🔍 Fuzzy searching for '{search_term}' across {len(system_dirs)} systems...")
        
    print("-" * 50)

    matched_games = []

    for system_dir in sorted(system_dirs):
        gamelist_xml = system_dir / "gamelist.xml"
        if not gamelist_xml.exists():
            continue

        system_name = system_dir.name

        try:
            with open(gamelist_xml, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except UnicodeDecodeError:
            print(f"  ⚠️ Skipping {system_name}: Unable to read file (invalid encoding).")
            continue

        # Bypass ES-DE <alternativeEmulator> outer tag issue by wrapping the content
        xml_decl_match = re.match(r'^(<\?xml.*?\?>)\s*', raw_content, flags=re.IGNORECASE)
        if xml_decl_match:
            inner_content = raw_content[xml_decl_match.end():]
        else:
            inner_content = raw_content

        wrapped_content = f"<dummy_es_de_root>{inner_content}</dummy_es_de_root>"

        try:
            root = ET.fromstring(wrapped_content)
        except ET.ParseError as e:
            print(f"  ⚠️ Skipping {system_name}: Unable to parse XML. Error: {e}")
            continue

        for game in root.findall('.//game'):
            path_elem = game.find('path')
            name_elem = game.find('name')

            if path_elem is None or not path_elem.text:
                continue

            game_path = path_elem.text.strip()
            # Use XML name if available, otherwise fallback to filename for matching
            game_title = name_elem.text.strip() if name_elem is not None and name_elem.text else Path(game_path).stem

            # Check for a match using either Regex or Fuzzy logic
            is_match = False
            if use_regex:
                is_match = bool(regex_pattern.search(game_title))
            else:
                is_match = fuzzy_substring_match(search_term, game_title, cutoff)

            if is_match:
                # Format for ES-DE Collection: Remove './' and fix slashes
                clean_path = game_path[2:] if game_path.startswith('./') else game_path
                clean_path = clean_path.replace('\\', '/')

                # Construct mapping: %ROMPATH%/system_name/path/to/rom.ext
                collection_entry = f"%ROMPATH%/{system_name}/{clean_path}"
                matched_games.append((system_name, game_title, collection_entry))

    if not matched_games:
        print(f"❌ No games found matching '{search_term}'. No collection created.")
        return

    # Sort the results alphabetically by system, then by game title for a neat output
    matched_games.sort(key=lambda x: (x[0], x[1]))

    # --- PREVIEW SECTION ---
    print("\n" + "=" * 50)
    print("🎮 PREVIEW: Games to be added to the collection")
    print("=" * 50)
    
    current_system = None
    for sys_name, title, _ in matched_games:
        if sys_name != current_system:
            print(f"\n📂 System: {sys_name}")
            current_system = sys_name
        print(f"  - {title}")

    print("\n" + "=" * 50)
    print(f"Total Matches Found: {len(matched_games)}")
    print("=" * 50 + "\n")

    # --- CONFIRMATION SECTION ---
    if not auto_confirm:
        while True:
            choice = input(f"Do you want to create/overwrite '{cfg_filename}'? [Y/n]: ").strip().lower()
            if choice in ['y', 'yes', '']:
                break
            elif choice in ['n', 'no']:
                print("❌ Operation cancelled. No collection was created.")
                return
            else:
                print("Please enter 'Y' or 'n'.")

    # --- FILE CREATION ---
    with open(cfg_output_path, 'w', encoding='utf-8') as f:
        for _, _, entry in matched_games:
            f.write(entry + '\n')

    print(f"\n✅ Collection created successfully at: \n💾 {cfg_output_path}")

    # --- UPDATE SETTINGS ---
    update_es_settings(esde_path, clean_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create an ES-DE custom collection based on fuzzy or regex search through gamelists."
    )
    parser.add_argument(
        "--esde-dir",
        required=True,
        type=str,
        help="The path to your es-de configuration directory (containing gamelists/ and collections/)"
    )
    parser.add_argument(
        "search_term",
        type=str,
        help="The term to fuzzy search for (e.g., 'zelda'), or a regex pattern if --regex is used."
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="Optional. The exact name of the collection (e.g., 'Favorites'). Will be prefixed with 'custom-' automatically."
    )
    parser.add_argument(
        "--cutoff",
        type=float,
        default=0.80,
        help="Fuzzy match threshold (0.0 to 1.0). Default is 0.80. Lower it to allow looser matches. Ignored if --regex is used."
    )
    parser.add_argument(
        "--regex", "-r",
        action="store_true",
        help="Treat the search term as a regular expression. Use '\\bWord\\b' for exact word matching."
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip the preview confirmation prompt and immediately create the collection."
    )

    args = parser.parse_args()
    create_collection(args.esde_dir, args.search_term, args.name, args.cutoff, args.yes, args.regex)
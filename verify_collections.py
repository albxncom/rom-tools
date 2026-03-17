import argparse
import os
from pathlib import Path
from utils import find_suggestion

def resolve_rom_path(cfg_path_str: str, roms_dir: Path) -> Path:
    """
    Attempts to map a path from the ES-DE collection file to the actual
    ROM directory, handling specific ES-DE variables.
    """
    if cfg_path_str.startswith("%ROMPATH%/"):
        relative_path = cfg_path_str[10:] 
        return roms_dir / relative_path
        
    if cfg_path_str.startswith("./"):
        relative_path = cfg_path_str[2:] 
        return roms_dir / relative_path

    original_path = Path(cfg_path_str)
    parts = original_path.parts
    parts_lower = [p.lower() for p in parts]
    
    try:
        roms_idx = parts_lower.index('roms')
        relative_parts = parts[roms_idx + 1:]
        return roms_dir.joinpath(*relative_parts)
    except ValueError:
        if original_path.is_absolute():
            return original_path
        return roms_dir.parent / original_path

def verify_collections(esde_dir: str, roms_dir: str, auto_replace: bool):
    esde_path = Path(esde_dir).resolve()
    roms_path = Path(roms_dir).resolve()
    
    collections_dir = esde_path / "collections"

    if not esde_path.exists():
        print(f"❌ Error: ES-DE directory not found at '{esde_path}'")
        return

    if not collections_dir.exists():
        print(f"❌ Error: Collections directory not found at '{collections_dir}'")
        return

    if not roms_path.exists():
        print(f"❌ Error: ROMs directory not found at '{roms_path}'")
        return

    cfg_files = list(collections_dir.glob("*.cfg"))
    if not cfg_files:
        print(f"⚠️ No collection (.cfg) files found in '{collections_dir}'.")
        return

    valid_cfg_files = [f for f in cfg_files if not f.name.startswith("._")]

    print(f"🔍 Searching for ROMs in: {roms_path}")
    print(f"📂 Found {len(valid_cfg_files)} collection(s). Starting verification...\n")
    if auto_replace:
        print("⚠️  AUTO-REPLACE IS ON. Files will be modified automatically.\n")
    print("-" * 50)

    total_missing = 0
    total_replaced = 0
    total_roms = 0

    for cfg_file in sorted(valid_cfg_files):
        print(f"📁 Verifying: {cfg_file.name}")
        
        try:
            with open(cfg_file, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
        except UnicodeDecodeError:
            print(f"  ⚠️ Skipping {cfg_file.name}: Unable to read file (invalid encoding).")
            print("-" * 50)
            continue

        missing_in_collection = []
        new_lines = []
        valid_entries_count = 0
        modifications_made = 0

        for line in lines:
            stripped_line = line.strip()
            if not stripped_line or stripped_line.startswith('#'):
                new_lines.append(line) # Keep empty lines and comments intact
                continue
            
            valid_entries_count += 1
            total_roms += 1
            
            actual_path = resolve_rom_path(stripped_line, roms_path)
            
            if not actual_path.exists():
                expected_dir = actual_path.parent
                suggestion = find_suggestion(actual_path, expected_dir)
                replaced = False
                
                if suggestion and auto_replace:
                    # Reconstruct the line preserving the ES-DE specific prefix directory
                    if '/' in stripped_line:
                        parent_dir = stripped_line.rsplit('/', 1)[0]
                        new_line = f"{parent_dir}/{suggestion}"
                    elif '\\' in stripped_line:
                        parent_dir = stripped_line.rsplit('\\', 1)[0]
                        new_line = f"{parent_dir}\\{suggestion}"
                    else:
                        new_line = suggestion
                        
                    new_lines.append(new_line)
                    modifications_made += 1
                    total_replaced += 1
                    replaced = True
                else:
                    new_lines.append(line)
                
                missing_in_collection.append((stripped_line, suggestion, replaced))
                total_missing += 1
            else:
                new_lines.append(line)

        # Output logic for the current collection
        if missing_in_collection:
            print(f"  ❌ Found {len(missing_in_collection)} missing ROM(s) out of {valid_entries_count}:")
            for original, suggestion, replaced in missing_in_collection:
                filename = Path(original).name
                display_path = filename if len(filename) < 60 else f"...{filename[-57:]}"
                
                if replaced:
                    print(f"    🔄 Replaced: {display_path} -> {suggestion}")
                else:
                    print(f"    - {display_path}")
                    if suggestion:
                        print(f"      💡 Suggestion: {suggestion}")
        else:
            if valid_entries_count == 0:
                print("  ⚠️ Collection is empty.")
            else:
                print(f"  ✅ All {valid_entries_count} ROM(s) found.")
                
        # Write back changes if replacements were made
        if auto_replace and modifications_made > 0:
            with open(cfg_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines) + '\n')
            print(f"  💾 Saved {modifications_made} replacements to {cfg_file.name}")
            
        print("-" * 50)

    print("\n📊 SUMMARY")
    print(f"Total Collections Checked: {len(valid_cfg_files)}")
    print(f"Total ROMs Processed: {total_roms}")
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
        print("All ROMs are perfectly in sync! ✅")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify ES-DE collection ROMs against your actual ROMs directory."
    )
    parser.add_argument(
        "--esde-dir", 
        required=True,
        type=str, 
        help="The path to your es-de configuration directory (containing collections/)"
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
        help="Automatically apply suggestions and modify the .cfg files."
    )
    
    args = parser.parse_args()
    verify_collections(args.esde_dir, args.roms_dir, args.replace)
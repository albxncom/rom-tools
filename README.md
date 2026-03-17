# ES-DE ROM Verification Tools

This repository contains Python utility scripts designed to generate, verify, and synchronize EmulationStation Desktop Edition (ES-DE) configuration files with an actual ROMs directory. It is particularly useful for maintaining emulation setups across devices where ROM files may have been renamed, moved, or are located on separate drives.

## Scripts

* **`create_collection.py`**: Generates a custom collection `.cfg` file by executing a fuzzy or RegEx search across your gamelist metadata.
* **`verify_collections.py`**: Scans ES-DE `.cfg` collection files to ensure all referenced ROM paths physically exist.
* **`verify_gamelists.py`**: Scans ES-DE `gamelist.xml` files across all system directories to verify that the referenced game paths physically exist.

Both verification scripts utilize fuzzy matching to detect closely named files and can suggest or automatically apply corrections for broken paths.

---

## Directory Assumptions

These tools allow you to specify exact paths, making them compatible with any OS or filesystem layout. 
* `--roms-dir`: The root folder containing your system-specific ROM folders (e.g., `nes`, `snes`, `psx`).
* `--esde-dir`: The configuration folder for ES-DE. The scripts assume standard ES-DE subfolders exist inside this directory:
  * `/collections/` (contains custom `.cfg` files)
  * `/gamelists/` (contains system-specific folders with `gamelist.xml` files)
  * `/settings/` (contains `es_settings.xml`)

---

## Usage Examples

### 1. Verifying Collections

Checks if games listed in your `.cfg` files exist in your ROM folder.

```bash
# Basic verification
python verify_collections.py --esde-dir /path/to/es-de --roms-dir /path/to/ROMs

# Automatically fix broken paths
python verify_collections.py --esde-dir /path/to/es-de --roms-dir /path/to/ROMs --replace
```

### 2. Verifying Gamelists

Scans all your `gamelist.xml` files and ensures the `<path>` tags point to real files.

```bash
# Basic verification
python verify_gamelists.py --esde-dir /path/to/es-de --roms-dir /path/to/ROMs

# Automatically fix broken paths inside the XMLs
python verify_gamelists.py --esde-dir /path/to/es-de --roms-dir /path/to/ROMs --replace
```

### 3. Creating a Custom Collection

Searches through your gamelists to bundle related games into a custom collection. It only needs the `es-de` directory to read your metadata.

```bash
# Fuzzy search for 'Zelda' and create a collection
python create_collection.py --esde-dir /path/to/es-de "Zelda"

# Search using RegEx and assign a specific collection name
python create_collection.py --esde-dir /path/to/es-de "\bmario\b" --regex --name "Mario Core Games"
```

## Options

### Shared Arguments
* `--esde-dir`: **Required**. Path to the main ES-DE configuration folder.
* `--roms-dir`: **Required** (for verification scripts). Path to your main ROMs directory.

### Verification Specific Flags (`verify_*.py`)
* `--replace`: Append this flag to automatically apply the suggested path corrections and modify the corresponding `.cfg` or `.xml` files.

### Collection Specific Flags (`create_collection.py`)
* `--name`: Optional. Set the exact name of the collection (e.g., `Favorites`). It will be automatically prefixed with `custom-`.
* `--cutoff`: Set the fuzzy match threshold (0.0 to 1.0). Default is `0.80`. Lower it to allow looser matches.
* `--regex` (`-r`): Treat the search term as a regular expression.
* `--yes` (`-y`): Skip the preview confirmation prompt and immediately write the file.

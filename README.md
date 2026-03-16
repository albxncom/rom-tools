# ES-DE ROM Verification Tools

This repository contains Python utility scripts designed to verify and synchronize EmulationStation Desktop Edition (ES-DE) configuration files with an actual ROMs directory. It is particularly useful for maintaining emulation setups (such as on an Ayaneo device) where ROM files may have been renamed or moved.

## Scripts

* **`verify_collections.py`**: Scans ES-DE `.cfg` collection files to ensure all referenced ROM paths exist.
* **`verify_gamelists.py`**: Scans ES-DE `gamelist.xml` files across all system directories to verify that the referenced game paths exist.

Both scripts utilize fuzzy matching to detect closely named files and can suggest or automatically apply corrections for broken paths.

## Usage

Run either script from the command line, providing the root directory of your emulation setup (the directory containing both the `ROMs` and `es-de` folders).

```bash
# Verify collections
python verify_collections.py /path/to/root_dir

# Verify gamelists
python verify_gamelists.py /path/to/root_dir
```

### Options

* `--replace`: Append this flag to automatically apply the suggested path corrections and modify the corresponding `.cfg` or `.xml` files.

```bash
python verify_gamelists.py /path/to/root_dir --replace
```

## Directory Structure
The scripts expect a standard ES-DE folder structure within the provided root directory:
* `/ROMs/` - Contains system-specific ROM folders.
* `/es-de/collections/` - Contains custom `.cfg` collection files.
* `/es-de/gamelists/` - Contains system-specific folders with `gamelist.xml` files.

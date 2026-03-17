import re
import difflib
from pathlib import Path
from typing import Optional

def fuzzy_substring_match(query: str, target: str, cutoff: float = 0.80) -> bool:
    """
    Returns True if the query is found within the target string using a 
    word-based chunking approach to eliminate character-overlap false positives.
    """
    query = query.lower().strip()
    target = target.lower().strip()

    # 1. Easy out: Exact substring match
    if query in target:
        return True

    # Strip punctuation for cleaner word tokenization
    clean_query = re.sub(r'[^\w\s]', '', query)
    clean_target = re.sub(r'[^\w\s]', '', target)

    # 2. Space-agnostic exact match 
    if clean_query.replace(" ", "") in clean_target.replace(" ", ""):
        return True

    query_words = clean_query.split()
    target_words = clean_target.split()

    if not query_words or not target_words:
        return False

    # 3. Word-chunk sliding window
    window_sizes = [len(query_words) - 1, len(query_words), len(query_words) + 1]
    window_sizes = [w for w in window_sizes if w > 0]

    for w_size in window_sizes:
        for i in range(len(target_words) - w_size + 1):
            window = " ".join(target_words[i:i+w_size])
            ratio = difflib.SequenceMatcher(None, clean_query, window).ratio()
            if ratio >= cutoff:
                return True

    return False

def clean_title(filename: str) -> str:
    """
    Removes the file extension and anything inside () or [] brackets
    to get the clean base title for fuzzy matching.
    """
    name = Path(filename).stem
    clean = re.sub(r'\(.*?\)|\[.*?\]', '', name).strip()
    return clean

def find_suggestion(missing_file_path: Path, expected_dir: Path, cutoff: float = 0.6) -> Optional[str]:
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
    
    # Find the closest match using difflib
    matches = difflib.get_close_matches(missing_clean, clean_to_actual.keys(), n=1, cutoff=cutoff)
    
    if matches:
        return clean_to_actual[matches[0]]
    return None
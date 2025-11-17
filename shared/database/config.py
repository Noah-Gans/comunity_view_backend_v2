from pathlib import Path

BASE_DIR = Path(__file__).parent / "teton_county_id_download"
TETON_IDAHO_DATA_DIR = str((BASE_DIR / "data").resolve())
TETON_IDAHO_PROCESSED_DIR = str((BASE_DIR / "processed").resolve())


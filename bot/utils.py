from pathlib import Path


def get_csv_filenames(path: Path | str) -> list[str]:
    path = Path(path)
    csv_filepath_generator = path.glob("*.csv")
    return [csv_filepath.name for csv_filepath in csv_filepath_generator]


def file_count(path: Path | str) -> int:
    path = Path(path)
    return len(list(path.iterdir()))


def chest(rank: int) -> str:
    if 1 <= rank <= 500:
        return "Diamond"
    elif 501 <= rank <= 1000:
        return "Platinum"
    elif 1001 <= rank <= 2000:
        return "Crystal"
    elif 2001 <= rank <= 3000:
        return "Titanium"
    elif rank >= 3001:
        return "Obsidian"

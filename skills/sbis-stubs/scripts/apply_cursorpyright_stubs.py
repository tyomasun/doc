import argparse
import json
from pathlib import Path

DEFAULT_SETTINGS = r"C:/Users/an.kochetovskiy/AppData/Roaming/Cursor/User/settings.json"
DEFAULT_STUBS = r"C:/Saby/stubs"


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"settings.json is not valid JSON (comments are not supported): {path}\n{exc}"
        )


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply Cursor Pyright stub settings for SBIS/Saby stubs."
    )
    parser.add_argument("--settings", default=DEFAULT_SETTINGS)
    parser.add_argument("--stubs", default=DEFAULT_STUBS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    settings_path = Path(args.settings)
    stubs_path = args.stubs

    settings = load_settings(settings_path)

    settings["cursorpyright.analysis.stubPath"] = stubs_path

    extra_paths = ensure_list(settings.get("cursorpyright.analysis.extraPaths"))
    if stubs_path not in extra_paths:
        extra_paths.append(stubs_path)
    settings["cursorpyright.analysis.extraPaths"] = extra_paths

    if args.dry_run:
        print(json.dumps(settings, ensure_ascii=True, indent=4))
        return 0

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(settings, ensure_ascii=True, indent=4) + "\n",
        encoding="utf-8",
    )
    print(f"Updated: {settings_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

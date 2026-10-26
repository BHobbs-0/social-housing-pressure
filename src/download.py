"""Download every source file listed in config.py into data/raw/ (skips files already present)."""
import sys
import urllib.request

import config


def all_urls():
    yield config.PRP_TREND
    yield config.PRP_GEO
    yield config.CORE_TENANCIES
    yield from config.HOMELESSNESS.values()


def main() -> int:
    config.RAW.mkdir(parents=True, exist_ok=True)
    failures = 0
    for url in all_urls():
        dest = config.raw_path(url)
        if dest.exists() and dest.stat().st_size > 0:
            print(f"  have  {dest.name}")
            continue
        try:
            tmp = dest.with_suffix(dest.suffix + ".part")
            with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                f.write(r.read())
            tmp.rename(dest)
            print(f"  got   {dest.name}")
        except Exception as e:  # report and carry on so one dead link doesn't stop the run
            failures += 1
            print(f"  FAIL  {dest.name}: {e}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

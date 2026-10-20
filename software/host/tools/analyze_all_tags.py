"""
Runs the standard analysis on a session that was started with --tag. The crossover fit only uses untagged
runs (tags mark side experiments), so a temporary copy with the tags blanked is analysed and the results are
written into the original session's analysis/ folder.

    python tools/analyze_all_tags.py <session_dir>

Author: Jessica
"""
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rig import analysis as an


def main():
    src = Path(sys.argv[1])
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp) / src.name
        t.mkdir()
        for name in ("readings.csv", "runs.csv", "blocks.csv", "warmup.csv", "session.json"):
            if (src / name).exists():
                shutil.copy2(src / name, t / name)
        for name in ("runs.csv", "blocks.csv"):
            df = pd.read_csv(t / name, dtype=str, keep_default_na=False)
            df["tag"] = ""
            df.to_csv(t / name, index=False)
        an.analyze(t, out_dir=src / "analysis")
    print("analysis written to", src / "analysis")


if __name__ == "__main__":
    main()

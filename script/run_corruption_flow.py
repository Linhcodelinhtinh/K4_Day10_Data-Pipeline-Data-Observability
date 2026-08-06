from __future__ import annotations

from pathlib import Path
import sys

# Dam bao import duoc src module khi chay truc tiep tu script
root_dir = Path(__file__).resolve().parents[1]
src_dir = root_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from pipelines.corruption_flow import main

if __name__ == "__main__":
    main()

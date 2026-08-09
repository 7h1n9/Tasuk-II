from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend" / "tests" / "challenge_solvers"))
from solve_core_c01 import solve  # noqa: E402,F401

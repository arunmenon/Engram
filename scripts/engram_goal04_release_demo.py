"""G04 release and deployment journey on actual Engram HTTP/workers/Spanner.

Reuse the reviewed goal harness with explicit G04 fixtures; no direct artifact writes.
"""

from pathlib import Path

from engram_goal03_implementation_demo import main
from engram_goal04_fixtures import fixtures

if __name__ == "__main__":
    main(goal="G04", fixture_factory=fixtures, driver_path=Path(__file__))

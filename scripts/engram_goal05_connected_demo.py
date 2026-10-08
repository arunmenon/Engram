"""G05 connected journey through real HTTP/workers/Spanner; retain successful data."""

from pathlib import Path

from engram_goal03_implementation_demo import main
from engram_goal05_fixtures import fixtures

if __name__ == "__main__":
    main(goal="G05", fixture_factory=fixtures, driver_path=Path(__file__), retain_success=True)

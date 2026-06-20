"""Put the package (under docker/files) on the import path for tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docker" / "files"))

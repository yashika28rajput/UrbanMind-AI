import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Isolate side effects BEFORE the application is imported: the SQLAlchemy engine
# is created at import time, and the federated simulation writes checkpoints.
# Without this, running the test suite writes to the real project database and
# overwrites tracked files under models/federated/.
_TEST_RUNTIME_DIR = Path(tempfile.mkdtemp(prefix="urbanmind-tests-"))
atexit.register(shutil.rmtree, _TEST_RUNTIME_DIR, ignore_errors=True)
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_RUNTIME_DIR / 'test.sqlite3').as_posix()}"
os.environ["URBANMIND_FEDERATED_DIR"] = str(_TEST_RUNTIME_DIR / "federated")
os.environ.setdefault("AUTH_REQUIRED", "false")

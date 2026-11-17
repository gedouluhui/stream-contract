"""Run the local contract suite without installing into the global environment."""
from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
env = os.environ.copy()
env['PYTHONPATH'] = str(root / 'src')
raise SystemExit(subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=root, env=env).returncode)

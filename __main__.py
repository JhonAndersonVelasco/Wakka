"""Wakka package — allows running as python -m wakka"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import main
main()

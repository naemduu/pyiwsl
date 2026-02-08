from pathlib import Path

from pyiwsl.optics import parse_pmmanager_file

sample = Path(__file__).resolve().parent.parent.parent / "tests" / "optics" / "data_pmmanager.txt"
log = parse_pmmanager_file(sample)
print(log)
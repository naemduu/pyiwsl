from pathlib import Path

import numpy as np

from pyiwsl.optics import parse_pmmanager_file


def test_parse_pmmanager_file_smoke():
    sample = Path(__file__).resolve().parent / "data_pmmanager.txt"
    assert sample.exists(), f"no sample file: {sample}"

    log = parse_pmmanager_file(sample)

    assert "timestamp" in log.df.columns
    assert log.df.shape[0] > 0

    channel_cols = [c for c in log.df.columns if c != "timestamp"]
    assert len(channel_cols) >= 1

    assert np.issubdtype(log.df["timestamp"].dtype, np.number)


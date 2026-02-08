from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Union

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PMManagerLog:
    """Parsed PMManager log."""
    meta: Dict[str, str]
    stats: Dict[str, Dict[str, float]]
    df: pd.DataFrame


# Strict float token matcher (supports scientific notation)
_FLOAT_RE = re.compile(
    r"""
    ^[+-]?
    (?:
        (?:\d+\.\d*)|(?:\d*\.\d+)|(?:\d+)
    )
    (?:[eE][+-]?\d+)?$
""",
    re.VERBOSE,
)

# Extract first number from a messy cell (fallback)
_NUM_RE = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")


def _to_float_or_nan(s: str) -> float:
    s = s.strip()
    if not s:
        return np.nan
    if _FLOAT_RE.match(s):
        return float(s)
    return np.nan


def _cell_to_float(cell: str) -> float:
    """Convert a cell (possibly whitespace-only) to float, else NaN."""
    cell = (cell or "").strip()
    if not cell:
        return np.nan
    if _FLOAT_RE.match(cell):
        return float(cell)
    nums = _NUM_RE.findall(cell)
    return float(nums[0]) if nums else np.nan


def parse_pmmanager_file(
    path: Union[str, Path],
    *,
    encoding: str = "utf-8",
    errors: str = "ignore",
) -> PMManagerLog:
    """Read a PMManager log file and parse it."""
    p = Path(path)
    text = p.read_text(encoding=encoding, errors=errors)
    return parse_pmmanager_text(text)


def parse_pmmanager_text(
    text: str,
    *,
    channel_letters: Optional[Sequence[str]] = None,
    max_fallback_channels: int = 8,
) -> PMManagerLog:
    """
    Parse PMManager log text.

    Key point: data rows often have "blank cells" represented by huge whitespace.
    Using regex split on whitespace will DESTROY empty columns, so this parser
    uses fixed-width slicing derived from the header line positions.
    If that fails, it falls back to tab-splitting (which preserves empty cells).
    """
    lines = text.splitlines()

    meta: Dict[str, str] = {}
    stats: Dict[str, Dict[str, float]] = {}
    current_channel_for_stats: Optional[str] = None

    data_start_idx: Optional[int] = None
    header_line: Optional[str] = None
    inferred_channels_from_header: Optional[list[str]] = None

    # ---- 1) Find table header and parse meta/stats ----
    for i, raw in enumerate(lines):
        line = raw.rstrip("\n")

        # Detect data header
        if re.search(r"\bTimestamp\b", line) and re.search(r"\bChannel\b", line):
            header_line = line
            found = re.findall(r"\bChannel\s+([A-Z])\b", line, flags=re.IGNORECASE)
            if found:
                inferred_channels_from_header = [c.upper() for c in found]
            data_start_idx = i + 1
            break

        if line.strip().startswith(";"):
            content = line.strip()[1:].strip()

            # Channel X:Statistics header
            m_stat_hdr = re.match(
                r"Channel\s+([A-Z])\s*:\s*Statistics",
                content,
                re.IGNORECASE,
            )
            if m_stat_hdr:
                ch = m_stat_hdr.group(1).upper()
                current_channel_for_stats = ch
                stats.setdefault(ch, {})
                continue

            # Stats line containing Min/Max/Average/Std.Dev/Overrange
            if current_channel_for_stats and any(
                k in content for k in ("Min:", "Max:", "Average:", "Std.Dev.", "Overrange:")
            ):
                parts = [p.strip() for p in content.split(";") if p.strip()]
                for p in parts:
                    if ":" not in p:
                        continue
                    k, v = p.split(":", 1)
                    key = k.strip().lower().replace(" ", "")
                    v = v.strip()
                    nums = _NUM_RE.findall(v)
                    if nums:
                        stats[current_channel_for_stats][key] = float(nums[0])
                continue

            # Generic meta key/value
            if ":" in content:
                k, v = content.split(":", 1)
                meta[k.strip()] = v.strip()

    if data_start_idx is None or header_line is None:
        raise ValueError("Could not find data table header line containing 'Timestamp' and 'Channel'.")

    # ---- 2) Decide channel order ----
    if channel_letters is not None:
        chs = [str(c).upper() for c in channel_letters]
    elif inferred_channels_from_header:
        chs = inferred_channels_from_header
    else:
        # fallback: meta keys like "Channel A"
        meta_channels: list[str] = []
        for k in meta.keys():
            m = re.match(r"Channel\s+([A-Z])\b", k, re.IGNORECASE)
            if m:
                meta_channels.append(m.group(1).upper())
        meta_channels = sorted(set(meta_channels))
        chs = meta_channels if meta_channels else list("ABCDEFGH")[:max_fallback_channels]

    # ---- 3) Build fixed-width column slices from header positions ----
    # We locate the starting index of "Timestamp" and "Channel X" tokens in the header line.
    # Then we slice each data row by those boundaries to preserve empty cells.
    def _find_start_of_token(pattern: str, s: str) -> int:
        m = re.search(pattern, s, flags=re.IGNORECASE)
        return m.start() if m else -1

    # Start positions for each column
    starts: list[int] = []
    starts.append(_find_start_of_token(r"\bTimestamp\b", header_line))
    for ch in chs:
        starts.append(_find_start_of_token(rf"\bChannel\s+{re.escape(ch)}\b", header_line))

    fixed_width_ok = all(x >= 0 for x in starts) and len(set(starts)) == len(starts)

    key_order = ["timestamp"] + chs

    rows: list[dict] = []

    if fixed_width_ok:
        # Build mapping key -> (start, end)
        sorted_starts = sorted(starts)
        start_to_next = {
            sorted_starts[i]: (sorted_starts[i], sorted_starts[i + 1] if i + 1 < len(sorted_starts) else None)
            for i in range(len(sorted_starts))
        }
        key_to_start = {k: s for k, s in zip(key_order, starts)}

        for raw in lines[data_start_idx:]:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if line.lstrip().startswith(";") or line.lstrip().startswith("-"):
                continue

            # Slice cells by fixed-width boundaries
            cells: dict[str, str] = {}
            for k in key_order:
                s0 = key_to_start[k]
                a, b = start_to_next[s0]
                cells[k] = (line[a:b] if b is not None else line[a:])

            t = _cell_to_float(cells["timestamp"])
            if np.isnan(t):
                continue

            row = {"timestamp": float(t)}
            for ch in chs:
                row[ch] = _cell_to_float(cells[ch])
            rows.append(row)

    else:
        # Fallback: use TAB split (preserves empty cells). If no tabs, use multi-space split but
        # we cannot perfectly preserve empty columns in pure-space layout without header positions.
        for raw in lines[data_start_idx:]:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if line.lstrip().startswith(";") or line.lstrip().startswith("-"):
                continue

            if "\t" in line:
                parts = line.split("\t")  # preserves empties
                parts = [p.strip() for p in parts]
            else:
                # best-effort fallback
                parts = re.split(r"\s{2,}", line.strip())
                parts = [p.strip() for p in parts]

            if not parts:
                continue

            t = _to_float_or_nan(parts[0])
            if np.isnan(t):
                continue

            # pad to expected length
            expected = 1 + len(chs)
            if len(parts) < expected:
                parts = parts + [""] * (expected - len(parts))

            row = {"timestamp": float(t)}
            for i, ch in enumerate(chs, start=1):
                row[ch] = _cell_to_float(parts[i])
            rows.append(row)

    df = pd.DataFrame(rows)

    # Sort and aggregate duplicate timestamps
    if "timestamp" in df.columns and not df.empty:
        df = df.sort_values("timestamp")
        df = df.groupby("timestamp", as_index=False).mean(numeric_only=True)

    return PMManagerLog(meta=meta, stats=stats, df=df)

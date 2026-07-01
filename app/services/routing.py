"""Routing engine.

The BRD asks to "sort items sequentially by their location identifier". A naive
lexical sort breaks on un-padded numbers (e.g. Shelf_2 sorts after Shelf_10).
We build a *natural* sort key by splitting each location into alternating text
and numeric chunks, so Aisle_A-Bay_04-Shelf_2 < Aisle_A-Bay_04-Shelf_10.

This is a serpentine-free, single-pass ordering. It is deterministic and cheap;
a true travel-distance optimiser (TSP over aisle coordinates) is a documented
future enhancement.
"""

import re

_CHUNK_RE = re.compile(r"(\d+)")


def natural_key(location: str | None) -> list:
    """Return a mixed list of (str | int) chunks for natural ordering.

    None/empty locations sort last so unmapped lines don't derail the path.
    """
    if not location:
        return ["\uffff"]  # sorts after any real string
    parts = _CHUNK_RE.split(location)
    key: list = []
    for p in parts:
        if p == "":
            continue
        key.append(int(p) if p.isdigit() else p.lower())
    return key


def order_lines_by_route(lines: list) -> list:
    """Return the given OrderLine objects sorted into walk-path order.

    Accepts any objects exposing a `.location` attribute.
    """
    return sorted(lines, key=lambda ln: natural_key(getattr(ln, "location", None)))

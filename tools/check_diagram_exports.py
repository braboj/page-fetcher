"""Check that a committed diagram export came from the documented command.

Four rules, each reported under its own code:

    SCALE       a PNG whose size is not consistent with `--scale 2`
    EDGE        an `mxCell` with `edge="1"` and no `<mxGeometry>` child
    UNPAIRED    a `.drawio` with no `.png` beside it, or the reverse
    UNREADABLE  a `.drawio` whose geometry this cannot recover

Run it over the directory holding the sources and their exports:

    python tools/check_diagram_exports.py docs/assets

It reads the PNG's header rather than the image, so it needs neither
draw.io nor a display. What it does not do is check that an export is
current for its source: an edit moving nothing structural leaves every
measurement here unchanged, so a stale export needs a different check.

PLAYBOOK 3.9 covers why the scale rule is a band rather than an equality,
and carries the measurements behind its edges.
"""

import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# The documented export scale, and the band the recovered ratio must land
# in. The export crops to the content box rather than the page, so the
# scale is recovered by dividing the PNG by the box around the source's
# vertices and waypoints — close to what draw.io renders, not equal to it.
# The band is wide because it only has to separate two populations a factor
# of two apart, and the floor sits under 2.0 because that box is not a
# strict lower bound: one diagram renders 0.56% narrower than its geometry,
# and a floor resting on an inequality that does not quite hold would fail
# a good export to catch nothing a looser one misses.
SCALE = 2
FLOOR = 1.75
CEILING = 3.0

# The first eight bytes of any PNG. Checked rather than assumed, so that a
# file renamed to `.png` is reported instead of unpacked as one.
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# The signature, then IHDR's 4-byte length and 4-byte type, then the width
# and height as big-endian unsigned longs. IHDR is required to be the first
# chunk, so the offset is fixed and no chunk walk is needed.
HEADER_BYTES = 24


def _png_size(path: Path) -> tuple[int, int] | None:
    """Return a PNG's pixel dimensions, or None if it is not a PNG."""
    with path.open("rb") as handle:
        header = handle.read(HEADER_BYTES)

    if len(header) < HEADER_BYTES or not header.startswith(PNG_SIGNATURE):
        return None

    width, height = struct.unpack(">II", header[16:24])
    return width, height


def _content_box(model: ET.Element) -> tuple[float, float] | None:
    """Return the box enclosing a page's vertices and edge waypoints."""
    xs: list[float] = []
    ys: list[float] = []

    for cell in model.iter("mxCell"):
        geometry = cell.find("mxGeometry")
        if geometry is None:
            continue

        # Every vertex reaching here is parented to a layer, so its
        # geometry is already absolute. `_nested_vertices` is what makes
        # that true: a vertex inside a group is measured from the group,
        # not from the page.
        if cell.get("vertex") == "1":
            x = float(geometry.get("x") or 0)
            y = float(geometry.get("y") or 0)
            xs += [x, x + float(geometry.get("width") or 0)]
            ys += [y, y + float(geometry.get("height") or 0)]

        # Only the points under `Array as="points"` are coordinates. An
        # edge's own geometry is relative — it places the label on a scale
        # where 0 is the midpoint of the path — so reading its x and y as
        # coordinates would drag the box towards the origin.
        for array in geometry.findall("Array"):
            for point in array.findall("mxPoint"):
                xs.append(float(point.get("x") or 0))
                ys.append(float(point.get("y") or 0))

    if not xs or not ys:
        return None

    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    if width <= 0 or height <= 0:
        return None

    return width, height


def _nested_vertices(model: ET.Element) -> list[str]:
    """Return the ids of vertices whose geometry is not page-absolute."""
    vertices = {
        cell.get("id") for cell in model.iter("mxCell") if cell.get("vertex") == "1"
    }

    return sorted(
        cell.get("id") or "?"
        for cell in model.iter("mxCell")
        if cell.get("vertex") == "1" and cell.get("parent") in vertices
    )


def _check_scale(
    export: Path, size: tuple[int, int], box: tuple[float, float]
) -> list[tuple[str, str, str]]:
    """Return a violation per axis whose ratio falls outside the band."""
    found: list[tuple[str, str, str]] = []
    axes = (("width", size[0], box[0]), ("height", size[1], box[1]))

    for axis, pixels, extent in axes:
        ratio = pixels / extent
        if FLOOR <= ratio < CEILING:
            continue

        found.append(
            (
                export.as_posix(),
                "SCALE",
                f"{axis} {pixels}px is {ratio:.2f}x the {extent:.0f}px content "
                f"box; a --scale {SCALE} export lands in [{FLOOR}, {CEILING})",
            )
        )

    return found


def _check_export(source: Path, model: ET.Element) -> list[tuple[str, str, str]]:
    """Return `(path, code, text)` for every violation of one export."""
    name = source.as_posix()
    export = source.with_suffix(".png")

    if not export.exists():
        return [(name, "UNPAIRED", "no .png export beside it")]

    size = _png_size(export)
    if size is None:
        return [(export.as_posix(), "UNREADABLE", "not a PNG")]

    box = _content_box(model)
    if box is None:
        return [(name, "UNREADABLE", "no vertex or waypoint geometry")]

    return _check_scale(export, size, box)


def _check_source(source: Path) -> list[tuple[str, str, str]]:
    """Return `(path, code, text)` for every violation of one diagram."""
    name = source.as_posix()

    # The sources are committed files in this repository, not input from
    # anywhere else, and tier 1 keeps `dependencies` empty — so reaching
    # for defusedxml here would need an ADR to buy nothing (CLAUDE.md 2.4).
    try:
        root = ET.parse(source).getroot()  # noqa: S314
    except ET.ParseError as error:
        return [(name, "UNREADABLE", f"not well-formed XML: {error}")]

    # The export command names no page, so it takes the first one. A second
    # page would be silently unexported rather than wrongly exported, which
    # is still a claim this check cannot make.
    pages = root.findall("diagram")
    if len(pages) != 1:
        return [(name, "UNREADABLE", f"{len(pages)} pages; the export takes one")]

    # draw.io can store a page as a deflated base64 payload instead of
    # readable XML. Reporting it beats treating an unreadable page as a
    # page with nothing in it, which would pass.
    model = pages[0].find("mxGraphModel")
    if model is None:
        return [(name, "UNREADABLE", "compressed page; save it uncompressed")]

    found: list[tuple[str, str, str]] = []

    # PLAYBOOK 4.7 documents this as the trap that costs an afternoon: the
    # edge is dropped from the render with no warning and exit status zero,
    # so the export comes back missing one arrow and nothing says so.
    for cell in model.iter("mxCell"):
        if cell.get("edge") == "1" and cell.find("mxGeometry") is None:
            identifier = cell.get("id") or "?"
            found.append((name, "EDGE", f"edge {identifier} has no <mxGeometry>"))

    # A vertex inside a group is placed relative to that group, so folding
    # its raw geometry into the box would measure a diagram nobody drew.
    # Reported rather than corrected: offsetting through a parent chain is
    # more machinery than a repository with no grouped vertex needs, and
    # the wrong box would fail a good export as readily as pass a bad one.
    nested = _nested_vertices(model)
    if nested:
        joined = ", ".join(nested)
        found.append((name, "UNREADABLE", f"vertices nested in a group: {joined}"))
        return found

    found.extend(_check_export(source, model))
    return found


def check(directory: Path) -> list[tuple[str, str, str]]:
    """Return `(path, code, text)` for every violation in one directory."""
    found: list[tuple[str, str, str]] = []

    sources = sorted(directory.glob("*.drawio"))
    expected = {source.with_suffix(".png") for source in sources}

    # Checked from both sides. A `.png` whose source was never committed is
    # a diagram nobody else can change, which PLAYBOOK 4.7 calls out and
    # which walking the sources alone would never see.
    for export in sorted(directory.glob("*.png")):
        if export not in expected:
            found.append((export.as_posix(), "UNPAIRED", "no .drawio source beside it"))

    for source in sources:
        found.extend(_check_source(source))

    return found


def main(argv: list[str]) -> int:
    """Print every violation in the given directories; return an exit code."""
    if not argv:
        print(
            "usage: check_diagram_exports.py DIRECTORY [DIRECTORY ...]",
            file=sys.stderr,
        )
        return 2

    found = 0
    for name in argv:
        for path, code, text in check(Path(name)):
            print(f"{path}: {code}: {text}")
            found += 1

    if found:
        print(f"\n{found} diagram-export violation(s). See PLAYBOOK 4.7.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

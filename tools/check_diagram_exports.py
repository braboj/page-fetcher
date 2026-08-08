"""Check that a committed diagram export came from the documented command.

Four rules, each reported under its own code:

    SCALE       a PNG whose size is not consistent with `--scale 2`
    EDGE        an `mxCell` with `edge="1"` and no `<mxGeometry>` child
    UNPAIRED    a `.drawio` with no `.png` beside it, or the reverse
    UNREADABLE  a `.drawio` whose geometry this cannot recover

Run it over the directory holding the sources and their exports:

    python tools/check_diagram_exports.py docs/assets

PLAYBOOK 4.7 exports at `--scale 2 --border 10`. Two of the seven diagrams
were committed at the default scale instead and neither was caught by
review: every arrow and every label renders correctly at half the
resolution, so nothing about the image says it is wrong, and being a
smaller file it reads in the diffstat as a compression win — #149's PNG
went from 102 KB to 56 KB and looked like an improvement. ADR-020 already
requires reading the export before committing, and that rule caught
neither, because reading a render proves the arrows are there and the
arrows are there at any scale. The property that was wrong is not one the
image displays, which is what makes this a gate rather than a review note.

What the scale rule compares. The export crops to the drawing's content
box rather than to the page box, so `2 * pageWidth` is not the expected
width — chapter 3's business context is a 1440x680 page that exports to
2695x1077. What the file does yield is the box enclosing every vertex and
every edge waypoint, which comes close to what draw.io renders without
matching it: labels, shadows and stroke widths push the rendered bounds
outward, while a shape's painted extent can sit just inside its geometry.
Measured against `2 * (box + 2 * 10)` the seven committed exports land
between 0.994 and 1.016 — mostly above it, and the deployment view 0.56%
below. Closing that gap would mean reimplementing text metrics, so the
rule is a band rather than an equality.

Where the band's edges come from. Divided by the box alone, the seven land
between 2.026 and 2.112. The same sources at scale 1 land at half that:
the two committed that way measured 1.009 and 1.026. So the floor
separates two populations a factor of two apart and can sit anywhere
between them. It is at 1.75 rather than at 2.0 because the box is not a
strict lower bound — the deployment view proves it can exceed what gets
rendered — and a floor resting on an inequality that does not quite hold
would fail a legitimate commit to catch nothing a looser one misses. The
ceiling at 3.0 rejects an export taken at scale 3 or 4. It also assumes a
content box much larger than the border, which adds `4 * 10 / box` to the
ratio: 0.03 at the width of these diagrams, and enough to matter only
below about 100px — smaller than any single shape in any of them.

One thing this deliberately does not do: it does not check that a PNG was
exported from the current source. An edit that moves nothing structural
leaves the ratio in band, so a stale export is a different defect needing
a different check. This gates the scale, which is the one a reader cannot
see.
"""

import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# The export scale PLAYBOOK 4.7 specifies, and the band around it that the
# docstring derives. All three sit together so that changing the export
# command has one place to look.
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

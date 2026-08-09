import struct
import zlib
from pathlib import Path

import pytest
from check_diagram_exports import check

REPO_ROOT = Path(__file__).resolve().parent.parent

ASSETS = REPO_ROOT / "docs" / "assets"

MXFILE = """\
<mxfile host="Electron">
  <diagram name="Fixture" id="fixture">
    <mxGraphModel pageWidth="1600" pageHeight="1200">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
{cells}      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""

CELLS = """\
        <mxCell id="a" vertex="1" parent="1">
          <mxGeometry x="0" y="0" width="{width}" height="{height}" as="geometry" />
        </mxCell>
        <mxCell id="e1" edge="1" parent="1" source="a" target="a">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>
"""

# The same order of magnitude as a real chapter diagram, so the 10px border
# contributes as little to the ratio here as it does there.
BOX = (1000, 600)

BORDER = 20


def source(width: int = BOX[0], height: int = BOX[1], cells: str | None = None) -> str:
    """Return a one-page draw.io file whose content box is `width x height`."""
    if cells is None:
        cells = CELLS.format(width=width, height=height)

    return MXFILE.format(cells=cells)


def write_png(path: Path, width: int, height: int) -> None:
    """Write a PNG carrying nothing but a valid header of the given size."""
    header = struct.pack(">II", width, height) + bytes([8, 6, 0, 0, 0])
    chunk = (
        struct.pack(">I", 13)
        + b"IHDR"
        + header
        + struct.pack(">I", zlib.crc32(b"IHDR" + header))
    )
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk)


def scaled(scale: float, box: tuple[int, int] = BOX) -> tuple[int, int]:
    """Return the size draw.io exports a box at, for a given scale."""
    return round(scale * (box[0] + BORDER)), round(scale * (box[1] + BORDER))


def codes(
    directory: Path,
    text: str | None = None,
    size: tuple[int, int] | None = None,
) -> list[str]:
    """Return the violation codes the checker reports for one fixture pair."""
    (directory / "07_fixture.drawio").write_text(
        source() if text is None else text, encoding="utf-8"
    )
    if size is not None:
        write_png(directory / "07_fixture.png", *size)

    return [code for _, code, _ in check(directory)]


SCALES = [
    pytest.param(1, ["SCALE", "SCALE"], id="the-default-scale"),
    pytest.param(1.5, ["SCALE", "SCALE"], id="under-the-floor"),
    pytest.param(2, [], id="the-documented-scale"),
    pytest.param(3, ["SCALE", "SCALE"], id="over-the-ceiling"),
    pytest.param(4, ["SCALE", "SCALE"], id="well-over-the-ceiling"),
]


@pytest.mark.parametrize(("scale", "expected"), SCALES)
def test_only_scale_two_passes_the_band(tmp_path, scale, expected):
    assert codes(tmp_path, size=scaled(scale)) == expected


# The two sizes the repository actually shipped at the default scale, kept
# as the regression cases they are. Both rendered every arrow correctly,
# which is why reading the render passed them twice.
REGRESSIONS = [
    pytest.param((1320, 510), (1332, 523), id="business-context-at-scale-1"),
    pytest.param((1061, 740), (1074, 753), id="level1-building-blocks-at-scale-1"),
]


@pytest.mark.parametrize(("box", "png"), REGRESSIONS)
def test_the_historical_scale_one_exports_are_caught(tmp_path, box, png):
    assert codes(tmp_path, text=source(*box), size=png) == ["SCALE", "SCALE"]


@pytest.mark.parametrize(("box", "png"), REGRESSIONS)
def test_those_diagrams_pass_at_the_size_they_were_repaired_to(tmp_path, box, png):
    assert codes(tmp_path, text=source(*box), size=(png[0] * 2, png[1] * 2)) == []


def test_one_axis_alone_is_reported(tmp_path):
    # A source edited without re-exporting can leave one axis in band and
    # the other out, so the axes are measured separately rather than as an
    # area, where a shortfall on one could be absorbed by the other.
    assert codes(tmp_path, size=(scaled(2)[0], scaled(1)[1])) == ["SCALE"]


def test_an_edge_without_geometry_is_reported(tmp_path):
    cells = CELLS.format(width=BOX[0], height=BOX[1]).replace(
        """<mxCell id="e1" edge="1" parent="1" source="a" target="a">
          <mxGeometry relative="1" as="geometry" />
        </mxCell>""",
        '<mxCell id="e1" edge="1" parent="1" source="a" target="a" />',
    )
    assert codes(tmp_path, text=source(cells=cells), size=scaled(2)) == ["EDGE"]


def test_a_source_without_an_export_is_reported(tmp_path):
    assert codes(tmp_path) == ["UNPAIRED"]


def test_an_export_without_a_source_is_reported(tmp_path):
    write_png(tmp_path / "99_orphan.png", *scaled(2))
    assert codes(tmp_path, size=scaled(2)) == ["UNPAIRED"]


UNREADABLE = [
    pytest.param("<mxfile><diagram>", id="malformed-xml"),
    pytest.param(
        '<mxfile><diagram id="a">7VpNc9s2EP01mmkPzhAgKFJH</diagram></mxfile>',
        id="compressed-page",
    ),
    pytest.param(
        source().replace("</mxfile>", '<diagram name="Second" id="two" /></mxfile>'),
        id="more-pages-than-the-export-takes",
    ),
    pytest.param(
        MXFILE.format(cells=""),
        id="a-page-with-no-geometry-at-all",
    ),
]


@pytest.mark.parametrize("text", UNREADABLE)
def test_a_source_this_cannot_measure_is_reported(tmp_path, text):
    # Never passed over. A check whose whole purpose is that nothing slips
    # through unnoticed should not have a branch that stays quiet.
    assert codes(tmp_path, text=text, size=scaled(2)) == ["UNREADABLE"]


def test_a_vertex_nested_in_a_group_is_reported(tmp_path):
    # Its geometry is measured from the group rather than from the page,
    # so folding it into the box straight would size a diagram nobody
    # drew — and a wrong box fails a good export as readily as it passes a
    # bad one. The export here is the correct size for the box the check
    # would compute if it went ahead, so only the nesting can fail it.
    cells = CELLS.format(width=BOX[0], height=BOX[1]) + (
        '        <mxCell id="c" vertex="1" parent="a">\n'
        '          <mxGeometry x="10" y="10" width="50" height="50" as="geometry" />\n'
        "        </mxCell>\n"
    )
    found = codes(tmp_path, text=source(cells=cells), size=scaled(2))
    assert found == ["UNREADABLE"]


def test_a_file_that_is_not_a_png_is_reported(tmp_path):
    (tmp_path / "07_fixture.drawio").write_text(source(), encoding="utf-8")
    (tmp_path / "07_fixture.png").write_bytes(b"GIF89a is not a PNG")
    assert [code for _, code, _ in check(tmp_path)] == ["UNREADABLE"]


def test_an_edge_label_offset_is_not_read_as_a_coordinate(tmp_path):
    # An edge's own geometry is relative, placing the label on a scale
    # where 0 is the midpoint. Read as coordinates, the -0.5 below would
    # drag the box out to the origin and halve every ratio.
    cells = CELLS.format(width=BOX[0], height=BOX[1]).replace(
        '<mxGeometry relative="1" as="geometry" />',
        '<mxGeometry x="-0.5" y="20" relative="1" as="geometry" />',
    )
    assert codes(tmp_path, text=source(cells=cells), size=scaled(2)) == []


def test_the_committed_diagrams_conform():
    found = [f"{Path(path).name}: {code}: {text}" for path, code, text in check(ASSETS)]
    assert found == []


def test_every_committed_diagram_is_measured():
    # The rules above only reach a diagram that is present, so dropping a
    # source from docs/assets/ would make the assertion above pass by
    # leaving less to measure. Seven when the check was written.
    assert len(sorted(ASSETS.glob("*.drawio"))) >= 7

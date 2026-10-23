"""Build a small, text-extractable PDF in memory for tests (pypdf-only, no external tools)."""

from __future__ import annotations

import io

from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
)

SUMMARY_SENTENCES = [
    "7. Performance Data",
    "Standalone performance testing was conducted on 500 consecutive cases collected from 4 clinical sites.",
    "The retrospective, blinded, multicenter study used a reference standard established by consensus of three neuroradiologists with majority vote.",
    "The device achieved a sensitivity of 93.5% (95% CI: 91.2-95.1%) and a specificity of 89.0% (95% CI: 86.4-91.2%), exceeding the performance goal of 80% for each primary endpoint.",
    "The AUC was 0.95.",
    "A fully-crossed multi-reader multi-case reader study with 12 radiologists and a 4 week washout period was also performed.",
    "The predicate device is K183285.",
]


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(lines: list[str] | None = None) -> bytes:
    lines = lines or SUMMARY_SENTENCES
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        }
    )
    font_ref = writer._add_object(font)
    resources = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )
    page[NameObject("/Resources")] = resources
    ops = ["BT", "/F1 10 Tf", "40 750 Td", "12 TL"]
    for line in lines:
        ops.append(f"({_escape(line)}) Tj T*")
    ops.append("ET")
    stream = DecodedStreamObject()
    stream.set_data("\n".join(ops).encode("latin-1"))
    stream_ref = writer._add_object(stream)
    page[NameObject("/Contents")] = stream_ref
    page[NameObject("/MediaBox")] = ArrayObject(
        [NumberObject(0), NumberObject(0), FloatObject(612), FloatObject(792)]
    )
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

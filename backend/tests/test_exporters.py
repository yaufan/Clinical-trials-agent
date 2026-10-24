import io
import zipfile

from app.exporters import markdown_to_docx, render_protocol_markdown
from app.schemas.protocol_input import EXAMPLE_INPUT, ProtocolInput
from app.schemas.run import DraftSection, RunState


def test_markdown_render_and_docx_roundtrip():
    inp = ProtocolInput.model_validate(EXAMPLE_INPUT)
    st = RunState(run_id="r1", project_id="p1")
    st.sections = [
        DraftSection(
            key="synopsis",
            title_en="1. Synopsis",
            title_zh="摘要",
            markdown="### 標題\n\n**bold** and `code`\n\n- bullet\n\n| a | b |\n|---|---|\n| 1 | 2 |",
            citations=["TFDA 2020, p.3"],
        )
    ]
    md = render_protocol_markdown(inp, st)
    assert "NeuroDetect-CT AI" in md and "References" in md and "TFDA 2020, p.3" in md
    data = markdown_to_docx(md, title="Protocol")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode()
    assert "bold" in xml and "bullet" in xml and "NeuroDetect" in xml


def test_normalize_section_markdown_drops_duplicate_title_and_demotes_headings():
    from app.exporters.markdown import normalize_section_markdown

    md = "## 計畫書摘要 / 1. Protocol Synopsis\n\n# 背景\ntext\n\n```\n# not a heading\n```\n## sub"
    out = normalize_section_markdown(md, title_en="1. Protocol Synopsis", title_zh="計畫書摘要")
    assert not out.startswith("## 計畫書摘要")
    assert out.splitlines()[0] == "### 背景"
    assert "# not a heading" in out  # code block untouched
    assert out.splitlines()[-1] == "### sub"

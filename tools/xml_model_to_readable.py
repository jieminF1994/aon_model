#!/usr/bin/env python3
r"""Extract readable pseudo-code from PathWise model XML files.

The RILA ESG XML stores formulas as XML text with escaped whitespace such as
``\s`` and ``\r\n``. This script does not translate the model language into
Python; it unwraps the XML into browsable text files grouped by model section.
"""

from __future__ import annotations

import argparse
import html
import re
import xml.etree.ElementTree as ET
from pathlib import Path


def clean_text(value: str | None) -> str:
    """Decode XML/formula escaping used by the model export."""
    if not value:
        return ""
    text = html.unescape(value)
    text = text.replace("\\r\\n", "\n")
    text = re.sub(r"(?<!\\)\\n", "\n", text)
    text = re.sub(r"(?<!\\)\\t", "\t", text)
    text = re.sub(r"(?<!\\)\\s", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def safe_name(path: Path) -> str:
    name = path.with_suffix("").name
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def attrs(element: ET.Element) -> str:
    return " ".join(f'{key}="{value}"' for key, value in element.attrib.items())


def write_section(lines: list[str], title: str) -> None:
    lines.append("")
    lines.append(f"## {title}")
    lines.append("")


def extract_file(path: Path, out_dir: Path) -> Path:
    root = ET.parse(path).getroot()
    lines: list[str] = []

    lines.append(f"# {path}")
    lines.append("")
    lines.append(f"root: {root.tag} {attrs(root)}")

    datasources = root.findall(".//datasource")
    if datasources:
        write_section(lines, "Data Sources")
        for datasource in datasources:
            lines.append(f"- {datasource.attrib.get('name')} -> {datasource.attrib.get('file')}")
            for dataset in datasource.findall("./dataset"):
                lines.append(
                    "  - "
                    f"{dataset.attrib.get('name')} "
                    f"type={dataset.attrib.get('type')} "
                    f"size={dataset.attrib.get('size-type')}"
                )

    imports = root.findall(".//ImportCompLib")
    if imports:
        write_section(lines, "Imported Component Libraries")
        for imported in imports:
            lines.append(f"- {attrs(imported)}")

    udfs = root.findall(".//udf")
    if udfs:
        write_section(lines, "User-Defined Functions")
        for udf in udfs:
            lines.append(f"### {udf.attrib.get('name')}")
            lines.append("")
            lines.append("```text")
            lines.append(clean_text(udf.text))
            lines.append("```")
            lines.append("")

    tables = root.findall(".//table")
    if tables:
        write_section(lines, "Tables And Column Formulas")
        for table in tables:
            lines.append(f"### {table.attrib.get('name')} ({table.attrib.get('type')})")
            lines.append("")

            groups = table.findall("./column-groups/g")
            if groups:
                lines.append("column groups:")
                for group in groups:
                    definition = clean_text(group.text)
                    suffix = f" = {definition}" if definition else ""
                    lines.append(f"- {attrs(group)}{suffix}")
                lines.append("")

            columns = table.findall(".//c")
            if columns:
                lines.append("columns:")
                for column in columns:
                    formula = clean_text(column.text)
                    if formula:
                        lines.append(f"- {column.attrib.get('name')}: {formula}")
                    else:
                        lines.append(f"- {column.attrib.get('name')} ({attrs(column)})")
                lines.append("")

    params = root.findall(".//param")
    if params:
        write_section(lines, "Component Parameters")
        for param in params:
            value = clean_text(param.text)
            if value:
                lines.append(f"- {param.attrib.get('name')}: {value}")
            else:
                lines.append(f"- {attrs(param)}")

    result_maps = root.findall(".//result-map")
    if result_maps:
        write_section(lines, "Result Maps")
        for result_map in result_maps:
            lines.append(f"- model={result_map.attrib.get('model')} <- lib={result_map.attrib.get('lib')}")

    results = root.findall(".//result")
    if results:
        write_section(lines, "Results")
        for result in results:
            ref = result.attrib.get("ref")
            if ref:
                lines.append(f"- {result.attrib.get('name')}: {clean_text(ref)}")
            else:
                lines.append(f"- {attrs(result)}")

    out_path = out_dir / f"{safe_name(path)}.readable.md"
    out_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml_root", type=Path, help="XML file or directory containing XML files")
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=Path("rila/esg/readable_code"),
        help="Directory for extracted readable files",
    )
    args = parser.parse_args()

    xml_paths = [args.xml_root] if args.xml_root.is_file() else sorted(args.xml_root.rglob("*.xml"))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    written = [extract_file(path, args.out_dir) for path in xml_paths]
    print(f"Wrote {len(written)} files to {args.out_dir}")
    for path in written:
        print(path)


if __name__ == "__main__":
    main()

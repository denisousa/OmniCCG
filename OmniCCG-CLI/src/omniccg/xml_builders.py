from xml.dom import minidom
import xml.etree.ElementTree as ET
from typing import Optional


def build_no_clones_message(detector: Optional[str]) -> str:
    detector_name = (detector or "unspecified").strip() or "unspecified"

    root = ET.Element("result")
    ET.SubElement(root, "status").text = "no_clones_found"
    ET.SubElement(root, "detector").text = detector_name

    try:
        ET.indent(root, space="  ", level=0)  # type: ignore[attr-defined]
        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")
    except Exception:
        rough = ET.tostring(root, encoding="utf-8")
        reparsed = minidom.parseString(rough)
        return reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")


def build_genealogy_xml(lineages_xml: str, metrics_xml: str) -> str:
    def _normalize_whitespace(elem):
        if elem.text is not None and elem.text.strip() == "":
            elem.text = None
        if elem.tail is not None and elem.tail.strip() == "":
            elem.tail = None
        for c in list(elem):
            _normalize_whitespace(c)

    lineages_root = ET.fromstring(lineages_xml)
    metrics_root = ET.fromstring(metrics_xml)

    _normalize_whitespace(lineages_root)
    _normalize_whitespace(metrics_root)

    genealogy = ET.Element("genealogy")
    genealogy.append(lineages_root)
    genealogy.append(metrics_root)

    try:
        ET.indent(genealogy, space="  ", level=0)
        return ET.tostring(
            genealogy,
            encoding="utf-8",
            xml_declaration=True,
            short_empty_elements=False,
        ).decode("utf-8")
    except AttributeError:
        rough = ET.tostring(
            genealogy,
            encoding="utf-8",
            xml_declaration=True,
            short_empty_elements=False,
        )
        dom = minidom.parseString(rough)
        return dom.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

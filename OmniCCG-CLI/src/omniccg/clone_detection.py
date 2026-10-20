import os
import re
import shutil
import subprocess
from pathlib import Path
from xml.dom import minidom
import xml.etree.ElementTree as ET
from typing import List

import requests

from omniccg.models import Context
from omniccg.domain.CloneClass import CloneClass
from omniccg.domain.CloneFragment import CloneFragment
from omniccg.utils import printError
from omniccg.get_method_name import get_enclosing_java_method
from omniccg.process_languages.clean_cs_code import process_directory_cs
from omniccg.process_languages.clean_rb_code import process_directory_rb
from omniccg.process_languages.clean_py_code import process_directory_py


def _read_text_with_fallback(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def GetCloneFragment(filename: str, startline: int, endline: int) -> str:
    text = _read_text_with_fallback(filename)
    lines_out = [""]
    remove_ws = False
    for i, raw in enumerate(text.splitlines(True)):
        if i >= (startline - 1):
            base = raw.split("//", 1)[0]
            if base.strip() == "":
                continue
            line = base.rstrip()
            if remove_ws:
                line = line.lstrip()
                remove_ws = False
            if len(line) > 2 and line[-1] not in ";{":
                remove_ws = True
            else:
                line = line + "\n"
            lines_out.append(line)
        if i >= (endline - 1):
            break
    return "".join(lines_out)


def parse_simian_to_clones(simian_xml: str) -> None:
    raw = open(simian_xml, 'r', encoding='utf-8', errors='ignore').read()
    pos = raw.find("<simian")
    if pos == -1:
        pos = raw.find("<")
        if pos == -1:
            raise ValueError("Content does not appear to contain valid XML.")
    xml = raw[pos:]
    xml = re.sub(r"<!--.*?-->", "", xml, flags=re.DOTALL)
    xml = re.sub(r"<\?.*?\?>", "", xml, flags=re.DOTALL)

    clean_xml = xml.strip()
    root = ET.fromstring(clean_xml)
    check = root.find("check")
    if check is None:
        raise ValueError("Invalid XML: <check> node not found.")

    clones = ET.Element("clones")
    for set_node in check.findall("set"):
        class_el = ET.SubElement(clones, "class")
        for block in set_node.findall("block"):
            source_file = block.get("sourceFile")
            start = block.get("startLineNumber")
            end = block.get("endLineNumber")
            ET.SubElement(class_el, "source", {"file": source_file, "startline": start or "", "endline": end or ""})

    rough = ET.tostring(clones, encoding="utf-8")
    reparsed = minidom.parseString(rough)
    result_xml = reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
    with open(simian_xml, "w", encoding="utf-8") as f:
        f.write(result_xml)


def RunCloneDetection(ctx: Context, current_hash: str) -> None:
    s, p = ctx.settings, ctx.paths
    print("Starting clone detection:")

    out_dir = Path(p.clone_detector_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for item in out_dir.iterdir():
        if item.is_file():
            item.unlink()
    Path(p.clone_detector_xml).parent.mkdir(parents=True, exist_ok=True)

    det_api = s.detection_api
    if isinstance(det_api, str) and det_api.strip():
        url = det_api.rstrip("/") + "/clone-detection/trigger"
        try:
            print(f" >>> GET {url}?sha={current_hash}&repo={s.git_url}")
            r = requests.get(url, params={"sha": current_hash, "repo": s.git_url}, timeout=15)
            if 200 <= r.status_code < 300:
                os.makedirs(os.path.dirname(p.clone_detector_xml), exist_ok=True)
                with open(p.clone_detector_xml, "wb") as f:
                    f.write(r.content)
                print("External detection API trigger accepted. Result written.\n")
                return
            else:
                print(f"External detection API failed (HTTP {r.status_code}). Falling back to configured tool...")
        except Exception as e:
            print(f"External detection API error: {e}")
            print("Falling back to configured clone detection tool...")
            if not s.clone_detector_tool:
                print("No clone detector configured, defaulting to nicad")
                s.clone_detector_tool = "nicad"

    tool = (s.clone_detector_tool or "").casefold()

    if s.language == "py":
        process_directory_py(p.prod_data_dir)
    elif s.language == "cs":
        process_directory_cs(p.prod_data_dir)
    elif s.language == "rb":
        process_directory_rb(p.prod_data_dir)

    if tool == "nicad":
        print(" >>> Running nicad6...")
        os.makedirs(p.cur_res_dir, exist_ok=True)
        subprocess.run(
            ["./nicad6", "functions", s.language, p.prod_data_dir],
            cwd=Path(p.tools_dir) / "NiCad",
            check=True,
        )
        nicad_xml = f"{p.prod_data_dir}_functions-clones/production_functions-clones-0.30-classes.xml"
        shutil.move(nicad_xml, p.clone_detector_xml)
        shutil.rmtree(Path(f"{p.prod_data_dir}_functions-clones"), ignore_errors=True)

        for log_file in Path(p.data_dir).glob("*.log"):
            try:
                log_file.unlink()
            except (FileNotFoundError, PermissionError):
                pass

        xml_path = Path(p.clone_detector_xml)
        xml_path.write_text(xml_path.read_text(encoding="utf-8"), encoding="utf-8")
        return

    if tool == "simian":
        print(" >>> Running Simian...")
        simian_jar = os.path.join(p.tools_dir, 'simian', 'simian-4.0.0.jar')
        simian_command = f'java -jar {simian_jar} -formatter=xml -threshold=20 "{p.prod_data_dir}/**/*.java" > "{p.clone_detector_xml}"'
        os.system(simian_command)
        parse_simian_to_clones(p.clone_detector_xml)
        print("Finished clone detection.\n")
        return

    for f in Path(p.clone_detector_dir).iterdir():
        if f.is_file():
            f.unlink()
    print("Finished clone detection.\n")


def parseCloneClassFile(cloneclass_filename: str) -> List[CloneClass]:
    cloneclasses: List[CloneClass] = []
    try:
        file_xml = ET.parse(cloneclass_filename)
        root = file_xml.getroot()
        for child in root:
            cc = CloneClass()
            fragments = list(child)
            if not fragments:
                continue
            for fragment in fragments:
                file_path = fragment.get("file")
                startline = int(fragment.get("startline"))
                endline = int(fragment.get("endline"))
                method_name = get_enclosing_java_method(file_path, startline, endline)
                cf = CloneFragment(file_path, startline, endline, method_name)
                cf.function_hash = hash(GetCloneFragment(cf.file, cf.ls, cf.le))
                cc.fragments.append(cf)
            cloneclasses.append(cc)
    except Exception as e:
        printError("Something went wrong while parsing the clonepair dataset:")
        raise e
    return cloneclasses


def CheckDoubleMatch(cc_original: CloneClass, cc1: CloneClass, cc2: CloneClass) -> int:
    cc1_strict_match = False
    cc2_strict_match = False
    for fragment in cc_original.fragments:
        for f1 in cc1.fragments:
            if fragment.matchesStrictly(f1):
                cc1_strict_match = True
        for f2 in cc2.fragments:
            if fragment.matchesStrictly(f2):
                cc2_strict_match = True
    if cc1_strict_match == cc2_strict_match:
        return 0
    if cc1_strict_match:
        return 1
    elif cc2_strict_match:
        return 2
    return 0

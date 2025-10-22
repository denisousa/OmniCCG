import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import re

def run(repo_path):
    print("Starting clone detection:")
    language = 'java'
    os.system('mkdir ' + CUR_RES_DIR)

    print(" > Production code:")
    print(" >>> Running nicad6...")
    os.system('cd tools/NiCad && ./nicad6 functions ' + language + ' ../../' + repo_path)

    # os.system('mv ' + repo_path + '_functions-clones/*.xml ' + CUR_RES_DIR)
    'workspace/dataset/production_functions-clones/production_functions-clones-0.30-classes.xml'
    NICAD_XML = repo_path + '_functions-clones/production_functions-clones-0.30-classes.xml'
    shutil.move(NICAD_XML, CLONE_DETECTOR_XML)

    # Clean up
    os.system('rm -rf ' + repo_path + '_functions-clones')
    os.system('rm ' + DATA_DIR + '/*.log')
    new_xml_data = open(CLONE_DETECTOR_XML, 'r').read().replace('../../', '')
    open(CLONE_DETECTOR_XML, 'w').write(new_xml_data)

    parse_simian_to_clones('clone_detector_result/result.xml')


def parse_simian_to_clones(simian_xml: str) -> str:
    raw = open(simian_xml, 'r').read()
    pos = raw.find("<simian")
    if pos == -1:
        pos = raw.find("<")
        if pos == -1:
            raise ValueError("Conteúdo não parece conter XML válido.")
    xml = raw[pos:]

    xml = re.sub(r"<!--.*?-->", "", xml, flags=re.DOTALL)
    xml = re.sub(r"<\?.*?\?>", "", xml, flags=re.DOTALL)

    clean_xml = xml.strip()
    root = ET.fromstring(clean_xml)

    # Navega até os <set> dentro de <check>
    check = root.find("check")
    if check is None:
        raise ValueError("XML inválido: nó <check> não encontrado.")

    clones = ET.Element("clones")

    # Para cada conjunto de blocos duplicados (<set>), criamos um <class>
    for set_node in check.findall("set"):
        class_el = ET.SubElement(clones, "class")

        # Cada <block> vira um <source>
        for block in set_node.findall("block"):
            source_file = block.get("sourceFile")
            start = block.get("startLineNumber")
            end = block.get("endLineNumber")

            ET.SubElement(
                class_el,
                "source",
                {
                    "file": source_file,
                    "startline": start if start else "",
                    "endline": end if end else "",
                },
            )

    # pretty print (com preservação simples)
    rough = ET.tostring(clones, encoding="utf-8")
    reparsed = minidom.parseString(rough)
    
    result_xml = reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
    with open("clone_detector_result/result.xml", "w", encoding="utf-8") as f:
        f.write(result_xml)
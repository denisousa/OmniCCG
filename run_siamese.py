import yaml
import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import os
import os
import subprocess
import time


elastic_path = 'tools/siamese'
os.system(f'rm -rf {elastic_path}/elasticsearch-2.2.0')

def download_elasticsearch_tar_gz():
    if not os.path.isfile(f'{elastic_path}/elasticsearch-2.2.0.tar.gz'):
        os.system('wget https://download.elasticsearch.org/elasticsearch/release/org/elasticsearch/distribution/tar/elasticsearch/2.2.0/elasticsearch-2.2.0.tar.gz')
        os.system(f'mv elasticsearch-2.2.0.tar.gz {elastic_path}/elasticsearch-2.2.0.tar.gz')

def unzip_elasticseaarch():
    if not os.path.isfile(f'{elastic_path}/elasticsearch-2.2.0'):
        command_unzip = f'tar -xvf {elastic_path}/elasticsearch-2.2.0.tar.gz -C {elastic_path}'
        os.system(command_unzip)

def download_elasticsearch():
    elasticsearch_yml_path = f'{elastic_path}/elasticsearch-2.2.0/config/elasticsearch.yml'
    elasticsearch_yml_content = f'cluster.name: stackoverflow'
    open(elasticsearch_yml_path, 'w').write(elasticsearch_yml_content)

    elasticsearch_in_sh_path = f'{elastic_path}/elasticsearch-2.2.0/bin/elasticsearch.in.sh'
    elasticsearch_content = open(elasticsearch_in_sh_path, 'r').read()
    elasticsearch_new_content = elasticsearch_content.replace('256m', '2g').replace('1g', '4g')
    open(elasticsearch_in_sh_path, 'w').write(elasticsearch_new_content)

download_elasticsearch_tar_gz()
unzip_elasticseaarch()
download_elasticsearch()
# os.system()

def run():
    os.system(f"{elastic_path}/elasticsearch-2.2.0/bin/elasticsearch -d")
    command = f"java -jar {elastic_path}/siamese-0.0.6-SNAPSHOT.jar -c index -cf {elastic_path}/config.properties"
    process = subprocess.Popen(
        command, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True
    )
    process.wait()
    time.sleep(1)
    command = f"java -jar {elastic_path}/siamese-0.0.6-SNAPSHOT.jar -c search -cf {elastic_path}/config.properties"
    process = subprocess.Popen(
        command, shell=True, stdin=None, stdout=None, stderr=None, close_fds=True
    )
    process.wait()
    os.system('rm -rf elasticsearch-2.2.0')

def parse_siamese_csv_to_xml() -> str:
    csv_text = open('search_results/test_qr_12-10-25_08-31-843.csv','r').read()
    root = Element("clones")

    # Process each CSV line as a <class>
    for raw_line in csv_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue  # skip blank lines

        class_el = SubElement(root, "class")

        # Each comma-separated token becomes a <source>
        for token in [t.strip() for t in line.split(",") if t.strip()]:
            try:
                file_and_rest = token.split("_", 1)
                file_path = file_and_rest[0]  # up to .java
                hash_parts = token.split("#")
                if len(hash_parts) < 3:
                    raise ValueError(f"Entry missing start/end lines: {token}")
                startline = hash_parts[-2]
                endline = hash_parts[-1]

                source = SubElement(class_el, "source")
                source.set("file", file_path)
                source.set("startline", startline)
                source.set("endline", endline)
            except Exception as e:
                # If parsing fails, you can choose to raise or skip.
                # Here we raise to surface malformed input early.
                raise ValueError(f"Could not parse entry: '{token}'. Error: {e}") from e

    # Pretty-print the XML
    rough = tostring(root, encoding="utf-8")
    parsed = minidom.parseString(rough)
    xml_txt = parsed.toprettyxml(indent="    ", encoding="utf-8").decode("utf-8")
    open('./clone_detector_result/result.xml', 'w').write(xml_txt)

run()
parse_siamese_csv_to_xml()

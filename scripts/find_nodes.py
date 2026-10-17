import subprocess, xml.etree.ElementTree as ET, re

subprocess.run(['adb', '-s', 'R9PW30T4JQM', 'shell', 'rm -f /data/local/tmp/dump.xml; uiautomator dump /data/local/tmp/dump.xml'], capture_output=True)
res = subprocess.run(['adb', '-s', 'R9PW30T4JQM', 'shell', 'cat /data/local/tmp/dump.xml'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
xml_str = res.stdout.decode('utf-8', errors='ignore')
try:
    root = ET.fromstring(xml_str)
    for node in root.iter('node'):
        txt = node.attrib.get('text', '')
        desc = node.attrib.get('content-desc', '')
        b = node.attrib.get('bounds', '')
        if any(w in txt.lower() or w in desc.lower() for w in ['upload', 'cancel', 'select', 'size:']):
            print(f"MATCH: text='{txt[:40]}' desc='{desc[:40]}' bounds='{b}'")
except Exception as e:
    print("Error:", e)

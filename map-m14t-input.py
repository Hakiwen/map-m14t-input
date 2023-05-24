import os
import re
import subprocess
from typing import Dict
import io


def get_input_ids(start_string):
    # Call 'xinput' command and get the output
    result = subprocess.run(['xinput'], stdout=subprocess.PIPE)
    device_output = result.stdout.decode('utf-8')

    lines = device_output.split('\n')
    device_ids = []
    for line in lines:
        if line.strip().find(start_string) != -1:
            device_id_start = line.find('id=') + 3
            device_id_end = line.find('\t', device_id_start)
            device_id = int(line[device_id_start:device_id_end])
            device_ids.append(device_id)
    return device_ids

def get_all_edids() -> Dict[str, bytes]:
    edids = {}

    xrandr = subprocess.run(
        ['xrandr', '--props'],
        check=True,
        stdout=subprocess.PIPE,
    )

    lines = [b.decode('utf-8') for b in xrandr.stdout.split(b'\n')]

    edid, connector_id = '', ''
    for line in lines:
        connector_match = re.match('^(?P<connector_id>\S+) connected', line)
        if connector_match:
            if edid and connector_id:
                edids[connector_id] = bytes.fromhex(edid)
            connector_id = connector_match.group('connector_id')
            edid = ''
        edid_match = re.match(r'\s*EDID:', line)
        if edid_match:
            edid = ''
        elif re.match(r'^\s*[0-9a-f]{32}$', line):
            edid += line.strip()
    if edid and connector_id:
        edids[connector_id] = bytes.fromhex(edid)
    return edids

def find_manufacturer(edid_map: Dict[str, bytes]):
    manufacturer_dict = {}
    for k, v in edid_map.items():

        process = subprocess.Popen(['edid-decode'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        process.stdin.write(io.BytesIO(v).read())
        process.stdin.close()
        result = process.stdout.read()
        result = result.decode()  # decode bytes to string

        match = re.search(r'Manufacturer: (\w+)', result)
        if match:
            manufacturer_code = match.group(1)
            manufacturer_dict[k] = manufacturer_code

    return manufacturer_dict

def set_input_mappings(input_ids: list, monitor_id: str) -> None:
    for in_id in input_ids:
        subprocess.run(['xinput', 'map-to-output', str(in_id), monitor_id],)

if __name__ == '__main__':
    input_device = 'Wacom Co.,Ltd.'
    monitor_man = "LEN"

    edids = get_all_edids()
    man_dict = find_manufacturer(edids)

    matching_keys = []
    for k, v in man_dict.items():
        if v == monitor_man:
            matching_keys.append(k)

    assert len(matching_keys) == 1, "Multiple Lenovo monitors attached, unable to determine the "
    monitor_id = matching_keys[0]

    input_ids_to_set = get_input_ids(input_device)
    set_input_mappings(input_ids_to_set, monitor_id)



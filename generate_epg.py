#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import re
import json
import time
import requests
from datetime import datetime, timedelta
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import fileinput

# إعداد المنطقة الزمنية
is_dst = time.localtime().tm_isdst > 0
utc_offset = - (time.altzone if is_dst else time.timezone)
offset_hours = utc_offset // 3600
offset_minutes = (abs(utc_offset) % 3600) // 60
time_zone = f"{offset_hours:+03d}{offset_minutes:02d}"

# تجاهل تحذيرات SSL
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# مسارات الملفات
input_path = "qatar1.xml"
output_path = "out.xml"
providers_file = "providers.json"

# قائمة التعديلات (يمكن تعديلها حسب الحاجة)
List_Chang = []

def download_epg():
    url = "https://www.open-epg.com/files/qatar1.xml"
    print("Downloading EPG file...")
    response = requests.get(url, verify=False)
    if response.status_code == 200:
        with io.open(input_path, 'w', encoding='utf-8') as f:
            f.write(response.content.decode('utf-8'))
        print("Download successful.")
    else:
        raise Exception(f"Failed to download EPG: {response.status_code}")

def apply_changes():
    for old_text, new_text in List_Chang:
        for line in fileinput.input(input_path, inplace=True):
            line = line.replace(old_text, new_text)
            print(line, end='')

def adjust_times():
    with io.open(input_path, 'r', encoding='utf-8') as f:
        xml_data = f.read()

    def shift_time(match, attr):
        dt = datetime.strptime(match.group(1), '%Y%m%d%H%M%S')
        sign = 1 if time_zone[0] == '+' else -1
        delta = timedelta(hours=sign * int(time_zone[1:3]), minutes=sign * int(time_zone[3:5]))
        dt += delta
        return f'{attr}="{dt.strftime("%Y%m%d%H%M%S")} {time_zone}"'

    xml_data = re.sub(r'start="(\d{14}) \+0000"', lambda m: shift_time(m, 'start'), xml_data)
    xml_data = re.sub(r'stop="(\d{14}) \+0000"', lambda m: shift_time(m, 'stop'), xml_data)

    with io.open(input_path, 'w', encoding='utf-8') as f:
        f.write(xml_data)

def remove_duplicates():
    seen = set()
    with open(output_path, 'w', encoding='utf-8') as out:
        for line in open(input_path, 'r', encoding='utf-8'):
            if line not in seen:
                out.write(line)
                seen.add(line)

def rename_final():
    os.remove(input_path)
    os.rename(output_path, input_path)
    print(f"Final file saved with timezone {time_zone}")

def update_provider_info():
    if not os.path.exists(providers_file):
        print("No providers.json found. Skipping.")
        return
    with open(providers_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for ch in data.get('bouquets', []):
        if ch.get('bouquet') == 'qatar1iet5':
            ch['date'] = datetime.now().strftime('%A %d %B %Y at %I:%M %p')
    with open(providers_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def clean_xml():
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    with open(input_path, 'w', encoding='utf-8') as f:
        for line in lines:
            if all(tag not in line for tag in ['<icon src="https://', '<url>https://', '<category']) and line.strip():
                f.write(line)

def main():
    try:
        download_epg()
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"Channel count: {content.count('<channel id=\"')}")
        apply_changes()
        adjust_times()
        remove_duplicates()
        rename_final()
        update_provider_info()
        clean_xml()
        print("EPG generation complete.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

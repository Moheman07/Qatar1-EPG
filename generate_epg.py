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

input_path = "qatar1.xml"
output_path = "out.xml"
providers_file = "providers.json"

warnings.filterwarnings('ignore', category=InsecureRequestWarning)

List_Chang = []

def download_epg():
    url = "https://www.open-epg.com/files/qatar1.xml"
    print("⬇️ Downloading EPG file...")
    response = requests.get(url, verify=False)
    if response.status_code == 200:
        with io.open(input_path, 'w', encoding='utf-8') as f:
            f.write(response.content.decode('utf-8'))
        print("✅ Download successful.")
    else:
        raise Exception(f"Failed to download EPG: {response.status_code}")

def apply_changes():
    # افتراضياً قائمة تحتوي على تغييرات التصنيف
    categories = {
        'Premier League': 'Football',
        'Formula 1': 'Motorsport',
        'UEFA Champions League': 'Football',
        'Bundesliga': 'Football',
        'La Liga': 'Football',
        'NBA': 'Basketball',
        'AFC': 'Football',
        'EFL': 'Football'
        # يمكن إضافة تصنيفات أخرى هنا
    }

    for old_text, new_text in List_Chang:
        for line in fileinput.input(input_path, inplace=True):
            line = line.replace(old_text, new_text)
            print(line, end='')

    # إضافة التصنيفات إلى البرنامج
    with open(input_path, 'r', encoding='utf-8') as f:
        xml_data = f.read()

    def add_category_to_programme(match):
        title = match.group(1)
        category = categories.get(title, 'Other')  # إذا لم يتوفر تصنيف، سيتم تصنيفه كـ 'Other'
        return f'<programme start="{match.group(2)}" stop="{match.group(3)}" channel="{match.group(4)}">\n<title>{title}</title>\n<category>{category}</category>\n<desc>{match.group(5)}</desc>\n</programme>'

    # تعديل البرامج وإضافة التصنيفات
    xml_data = re.sub(r'<programme start="(\d{14}) \+0000" stop="(\d{14}) \+0000" channel="([^"]+)"><title>([^<]+)</title><desc>([^<]+)</desc>', add_category_to_programme, xml_data)

    # حفظ التعديلات في الملف
    with open(input_path, 'w', encoding='utf-8') as f:
        f.write(xml_data)
    print("✅ تم إضافة التصنيفات للبرامج.")

def adjust_times():
    with io.open(input_path, 'r', encoding='utf-8') as f:
        xml_data = f.read()

    def adjust_time(match, attr):
        original_time = datetime.strptime(match.group(1), '%Y%m%d%H%M%S')
        # خصم 3 ساعات من التوقيت الأصلي
        adjusted_time = original_time - timedelta(hours=3)
        return f'{attr}="{adjusted_time.strftime("%Y%m%d%H%M%S")} +0000"'

    xml_data = re.sub(r'start="(\d{14}) \+0000"', lambda m: adjust_time(m, 'start'), xml_data)
    xml_data = re.sub(r'stop="(\d{14}) \+0000"', lambda m: adjust_time(m, 'stop'), xml_data)

    with io.open(input_path, 'w', encoding='utf-8') as f:
        f.write(xml_data)

    print("🕓 تم تعديل توقيت البرامج داخل XML (-3 ساعات)")

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
    print("📁 ملف XML النهائي تم حفظه.")

def update_provider_info():
    if not os.path.exists(providers_file):
        print("⚠️ لا يوجد ملف providers.json.")
        return
    with open(providers_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for ch in data.get('bouquets', []):
        if ch.get('bouquet') == 'qatar1iet5':
            ch['date'] = datetime.now().strftime('%A %d %B %Y - %H:%M')
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
            print(f"📺 عدد القنوات: {content.count('<channel id=\"')}")
        apply_changes()
        adjust_times()
        remove_duplicates()
        rename_final()
        update_provider_info()
        clean_xml()
        print("✅ EPG generation complete.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

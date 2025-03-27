#!/usr/bin/env python
import os
import requests
import json
import pandas as pd

# Create output directory
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Step 1: Fetch the main ICD-10 hierarchy
def fetch_icd10_hierarchy():
    url = "https://fat.kote.helsedirektoratet.no/api/code-systems/icd10/hierarchy"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Origin": "https://finnkode.helsedirektoratet.no"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

# Step 2: Find Chapter V and fetch its hierarchy
def fetch_chapter_v_hierarchy(hierarchy_data):
    # Look for Chapter V in the hierarchy
    chapter_v = None
    if 'children' in hierarchy_data:
        for child in hierarchy_data['children']:
            if child.get('codeValue') == 'V':
                chapter_v = child
                break
    
    if not chapter_v:
        print("Could not find Chapter V (Mental disorders) in the hierarchy")
        return None
    
    # Now fetch the specific hierarchy for Chapter V
    url = f"https://fat.kote.helsedirektoratet.no/api/code-systems/icd10/{chapter_v['codeValue']}/hierarchy"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Origin": "https://finnkode.helsedirektoratet.no"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

# Main function
def main():
    print("Fetching ICD-10 hierarchy...")
    main_hierarchy = fetch_icd10_hierarchy()
    
    if not main_hierarchy:
        print("Failed to fetch ICD-10 hierarchy")
        return
    
    print("Fetching Chapter V (Mental disorders) hierarchy...")
    chapter_v = fetch_chapter_v_hierarchy(main_hierarchy)
    
    if not chapter_v:
        print("Failed to fetch Chapter V hierarchy")
        return
    
    # Save the Chapter V hierarchy
    with open(os.path.join(OUTPUT_DIR, "chapter_v_hierarchy.json"), "w", encoding="utf-8") as f:
        json.dump(chapter_v, f, indent=2, ensure_ascii=False)
    print(f"Saved Chapter V hierarchy to {os.path.join(OUTPUT_DIR, 'chapter_v_hierarchy.json')}")
    
    # Look for F codes in the Chapter V hierarchy
    print("\nAnalyzing Chapter V structure:")
    print(f"Top-level keys: {list(chapter_v.keys())}")
    
    if 'children' in chapter_v:
        print(f"Number of children: {len(chapter_v['children'])}")
        for i, child in enumerate(chapter_v['children'][:5]):
            print(f"Child {i} code value: {child.get('codeValue')}")
            print(f"Child {i} name: {child.get('nameNorwegian')}")

if __name__ == "__main__":
    main()
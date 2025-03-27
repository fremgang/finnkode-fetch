#!/usr/bin/env python
"""
Direct API access script for retrieving mental disorder codes from Finnkode.
This script accesses the API endpoints directly using a similar approach to the Finnkode website.
"""
import os
import sys
import json
import pandas as pd
import requests
from datetime import datetime
import re

# Constants
OUTPUT_DIR = "analysis_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# API endpoints - these match what's used in the actual Finnkode website
BLOCK_API_URL = "https://fat.kote.helsedirektoratet.no/api/code-systems/icd10-blocks"
SECTION_API_URL = "https://fat.kote.helsedirektoratet.no/api/code-systems/icd10/sections-with-blocks"
CODE_API_URL = "https://fat.kote.helsedirektoratet.no/api/code-systems/icd10"

# Set up headers
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://finnkode.helsedirektoratet.no",
    "Referer": "https://finnkode.helsedirektoratet.no/",
    "Connection": "keep-alive"
}

def fetch_icd10_blocks():
    """
    Fetch all ICD-10 blocks (including F00-F09, F10-F19, etc.).
    
    Returns:
        list: List of block objects
    """
    print("Fetching ICD-10 blocks...")
    
    try:
        response = requests.get(BLOCK_API_URL, headers=API_HEADERS)
        
        if response.status_code == 200:
            blocks = response.json()
            print(f"Successfully fetched {len(blocks)} ICD-10 blocks")
            
            # Save raw blocks data for inspection
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            raw_file = os.path.join(OUTPUT_DIR, f"icd10_blocks_{timestamp}.json")
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(blocks, f, ensure_ascii=False, indent=2)
            print(f"Saved raw ICD-10 blocks to {raw_file}")
            
            return blocks
        else:
            print(f"Error {response.status_code} fetching ICD-10 blocks")
            return []
    except Exception as e:
        print(f"Error fetching ICD-10 blocks: {e}")
        return []

def fetch_sections_with_blocks():
    """
    Fetch ICD-10 sections with their blocks.
    
    Returns:
        list: List of section objects with blocks
    """
    print("Fetching ICD-10 sections with blocks...")
    
    try:
        response = requests.get(SECTION_API_URL, headers=API_HEADERS)
        
        if response.status_code == 200:
            sections = response.json()
            print(f"Successfully fetched {len(sections)} ICD-10 sections")
            
            # Save raw sections data for inspection
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            raw_file = os.path.join(OUTPUT_DIR, f"icd10_sections_{timestamp}.json")
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(sections, f, ensure_ascii=False, indent=2)
            print(f"Saved raw ICD-10 sections to {raw_file}")
            
            return sections
        else:
            print(f"Error {response.status_code} fetching ICD-10 sections")
            return []
    except Exception as e:
        print(f"Error fetching ICD-10 sections: {e}")
        return []

def find_mental_disorder_blocks(blocks, sections):
    """
    Find mental disorder blocks (F00-F99) from the fetched data.
    
    Args:
        blocks (list): List of block objects
        sections (list): List of section objects with blocks
        
    Returns:
        list: List of mental disorder block objects
    """
    print("Finding mental disorder blocks...")
    
    # First, find from blocks
    f_blocks = []
    
    if blocks:
        for block in blocks:
            if isinstance(block, dict) and 'code' in block:
                code = block.get('code', '')
                if isinstance(code, str) and code.startswith('F'):
                    f_blocks.append(block)
    
    print(f"Found {len(f_blocks)} mental disorder blocks from blocks API")
    
    # Then, check sections for mental disorders (Chapter V)
    section_f_blocks = []
    
    if sections:
        for section in sections:
            if isinstance(section, dict) and 'code' in section:
                code = section.get('code', '')
                if code == 'V' or 'mental' in section.get('name', '').lower() or 'psykisk' in section.get('name', '').lower():
                    print(f"Found mental disorder section: {code} - {section.get('name', '')}")
                    
                    # Check blocks in this section
                    for block in section.get('blocks', []):
                        if isinstance(block, dict) and 'code' in block:
                            block_code = block.get('code', '')
                            if isinstance(block_code, str) and block_code.startswith('F'):
                                section_f_blocks.append(block)
    
    print(f"Found {len(section_f_blocks)} mental disorder blocks from sections API")
    
    # Combine and deduplicate
    all_blocks = f_blocks + section_f_blocks
    unique_blocks = {}
    
    for block in all_blocks:
        if 'code' in block:
            unique_blocks[block['code']] = block
    
    result = list(unique_blocks.values())
    print(f"Total unique mental disorder blocks: {len(result)}")
    
    return result

def fetch_codes_for_block(block_code):
    """
    Fetch individual codes for a specific block.
    
    Args:
        block_code (str): Block code (e.g., 'F00-F09')
        
    Returns:
        list: List of code objects
    """
    print(f"Fetching codes for block: {block_code}")
    
    # First, extract the range from the block code
    match = re.match(r'([A-Z]\d+)-([A-Z]\d+)', block_code)
    if not match:
        print(f"Invalid block code format: {block_code}")
        return []
    
    start_code = match.group(1)
    end_code = match.group(2)
    
    # Determine the prefix and start/end numbers
    prefix = start_code[0]
    start_num = int(start_code[1:])
    end_num = int(end_code[1:])
    
    print(f"Block range: {prefix}{start_num} to {prefix}{end_num}")
    
    # Now get the individual codes
    all_codes = []
    
    for num in range(start_num, end_num + 1):
        code = f"{prefix}{num:02d}"
        
        # Try to fetch this code
        url = f"{CODE_API_URL}/{code}"
        try:
            response = requests.get(url, headers=API_HEADERS)
            
            if response.status_code == 200:
                code_data = response.json()
                all_codes.append(code_data)
                print(f"  Fetched {code}: {code_data.get('nameNorwegian', '')}")
                
                # If this code has children, fetch them too
                if not code_data.get('isLeafNode', True):
                    children_url = f"{CODE_API_URL}/{code}/children"
                    try:
                        children_response = requests.get(children_url, headers=API_HEADERS)
                        
                        if children_response.status_code == 200:
                            children = children_response.json()
                            print(f"    Found {len(children)} children for {code}")
                            all_codes.extend(children)
                            
                            # For each child, if it's not a leaf node, fetch its children too
                            for child in children:
                                if isinstance(child, dict) and 'codeValue' in child and not child.get('isLeafNode', True):
                                    child_code = child.get('codeValue', '')
                                    child_children_url = f"{CODE_API_URL}/{child_code}/children"
                                    
                                    try:
                                        child_children_response = requests.get(child_children_url, headers=API_HEADERS)
                                        
                                        if child_children_response.status_code == 200:
                                            child_children = child_children_response.json()
                                            print(f"      Found {len(child_children)} grandchildren for {child_code}")
                                            all_codes.extend(child_children)
                                    except Exception as e:
                                        print(f"      Error fetching grandchildren for {child_code}: {e}")
                    except Exception as e:
                        print(f"    Error fetching children for {code}: {e}")
            else:
                print(f"  Error {response.status_code} fetching {code}")
        except Exception as e:
            print(f"  Error fetching {code}: {e}")
    
    print(f"Total codes found for block {block_code}: {len(all_codes)}")
    return all_codes

def fetch_all_mental_disorder_codes():
    """
    Fetch all mental disorder codes from Finnkode.
    
    Returns:
        list: List of code objects
    """
    # Fetch blocks and sections
    blocks = fetch_icd10_blocks()
    sections = fetch_sections_with_blocks()
    
    # Find mental disorder blocks
    mental_blocks = find_mental_disorder_blocks(blocks, sections)
    
    if not mental_blocks:
        print("No mental disorder blocks found")
        return []
    
    # Fetch codes for each block
    all_codes = []
    
    for block in mental_blocks:
        block_code = block.get('code', '')
        block_name = block.get('name', '')
        print(f"\nProcessing block: {block_code} - {block_name}")
        
        block_codes = fetch_codes_for_block(block_code)
        all_codes.extend(block_codes)
    
    # Remove duplicates
    unique_codes = {}
    
    for code in all_codes:
        if isinstance(code, dict) and 'codeValue' in code:
            unique_codes[code['codeValue']] = code
    
    result = list(unique_codes.values())
    print(f"\nTotal unique mental disorder codes: {len(result)}")
    
    return result

def save_to_excel(codes, filename):
    """
    Save codes to Excel file.
    
    Args:
        codes (list): List of code objects
        filename (str): Output filename
        
    Returns:
        str: Path to the saved file
    """
    if not codes:
        print("No codes to save")
        return None
    
    # Extract relevant fields
    rows = []
    
    for code in codes:
        if isinstance(code, dict):
            row = {
                'codeValue': code.get('codeValue', ''),
                'nameNorwegian': code.get('nameNorwegian', ''),
                'active': code.get('active', False),
                'isLeafNode': code.get('isLeafNode', True)
            }
            rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Sort by code value
    if 'codeValue' in df.columns:
        df = df.sort_values('codeValue')
    
    # Save to Excel
    output_path = os.path.join(OUTPUT_DIR, filename)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Mental Disorder Codes', index=False)
    
    print(f"Saved data to {output_path}")
    return output_path

def main():
    """Main function."""
    print("Fetching mental disorder codes from Finnkode API...")
    
    # Fetch all mental disorder codes
    codes = fetch_all_mental_disorder_codes()
    
    if not codes:
        print("Failed to fetch mental disorder codes")
        return
    
    # Save to Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_file = f"mental_disorder_codes_{timestamp}.xlsx"
    save_to_excel(codes, excel_file)
    
    # Save as JSON for programmatic access
    json_file = os.path.join(OUTPUT_DIR, f"mental_disorder_codes_{timestamp}.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(codes, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON mental disorder codes to {json_file}")
    
    # Print summary statistics
    print("\nMental Disorder Code Statistics:")
    
    # Group codes by first three characters
    code_groups = {}
    
    for code in codes:
        if isinstance(code, dict) and 'codeValue' in code:
            code_value = code.get('codeValue', '')
            if len(code_value) >= 3:
                group_key = code_value[:3]
                if group_key in code_groups:
                    code_groups[group_key].append(code)
                else:
                    code_groups[group_key] = [code]
    
    print(f"Found {len(code_groups)} code groups (e.g., F00, F01, etc.)")
    
    # Print summary for each group
    for group_key, group_codes in sorted(code_groups.items()):
        if group_codes:
            group_name = group_codes[0].get('nameNorwegian', '')
            leaf_count = sum(1 for code in group_codes if code.get('isLeafNode', True))
            parent_count = len(group_codes) - leaf_count
            
            print(f"{group_key}: {group_name}")
            print(f"  Total codes: {len(group_codes)}")
            print(f"  Leaf nodes: {leaf_count}")
            print(f"  Parent nodes: {parent_count}")

if __name__ == "__main__":
    main()
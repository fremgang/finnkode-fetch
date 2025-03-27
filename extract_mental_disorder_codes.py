#!/usr/bin/env python
"""
Simplified direct access script for retrieving mental disorder codes from Finnkode.
This script targets the chapter V endpoint specifically.
"""
import os
import sys
import json
import pandas as pd
import requests
from datetime import datetime

# Constants
OUTPUT_DIR = "analysis_output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# API endpoint for Chapter V (Mental Disorders)
CHAPTER_V_API_URL = "https://fat.kote.helsedirektoratet.no/api/code-systems/icd10/V/hierarchy"

# Set up headers
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://finnkode.helsedirektoratet.no",
    "Referer": "https://finnkode.helsedirektoratet.no/",
}

def fetch_mental_disorders():
    """
    Fetch the mental disorder hierarchy directly from the Chapter V API.
    
    Returns:
        dict: Mental disorder hierarchy data
    """
    print("Fetching mental disorder hierarchy...")
    
    try:
        response = requests.get(CHAPTER_V_API_URL, headers=API_HEADERS)
        
        if response.status_code == 200:
            hierarchy = response.json()
            print("Successfully fetched mental disorder hierarchy")
            
            # Save raw hierarchy data for inspection
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            raw_file = os.path.join(OUTPUT_DIR, f"mental_disorders_hierarchy_{timestamp}.json")
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(hierarchy, f, ensure_ascii=False, indent=2)
            print(f"Saved raw hierarchy data to {raw_file}")
            
            return hierarchy
        else:
            print(f"Error {response.status_code} fetching mental disorder hierarchy")
            print(f"Response: {response.text[:200]}...")
            return None
    except Exception as e:
        print(f"Error fetching mental disorder hierarchy: {e}")
        return None

def extract_f_codes(hierarchy):
    """
    Extract F codes from the mental disorder hierarchy.
    
    Args:
        hierarchy (dict): Mental disorder hierarchy data
        
    Returns:
        list: List of F code objects
    """
    if not hierarchy:
        return []
    
    f_codes = []
    
    def process_node(node):
        if isinstance(node, dict) and 'codeValue' in node:
            code_value = node.get('codeValue', '')
            if isinstance(code_value, str) and code_value.startswith('F'):
                f_codes.append(node)
        
        if isinstance(node, dict) and 'children' in node and node['children']:
            for child in node['children']:
                process_node(child)
    
    # Process the hierarchy
    process_node(hierarchy)
    
    print(f"Extracted {len(f_codes)} F codes from hierarchy")
    return f_codes

def save_to_excel(codes, filename):
    """
    Save F codes to Excel file.
    
    Args:
        codes (list): List of F code objects
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
        row = {
            'codeValue': code.get('codeValue', ''),
            'nameNorwegian': code.get('nameNorwegian', ''),
            'active': code.get('active', False),
            'isLeafNode': code.get('isLeafNode', True),
            'sortIndex': code.get('sortIndex', 0)
        }
        
        # Add the path as a string if available
        if 'path' in code:
            row['path'] = ' > '.join(code['path'])
            
        rows.append(row)
    
    # Create DataFrame
    df = pd.DataFrame(rows)
    
    # Sort by code value
    if 'codeValue' in df.columns:
        df = df.sort_values('codeValue')
    
    # Save to Excel
    output_path = os.path.join(OUTPUT_DIR, filename)
    df.to_excel(output_path, index=False)
    
    print(f"Saved {len(df)} F codes to {output_path}")
    return output_path

def main():
    """Main function."""
    print("Fetching mental disorder codes from Finnkode API...")
    
    # Fetch the mental disorder hierarchy
    hierarchy = fetch_mental_disorders()
    
    if not hierarchy:
        print("Failed to fetch mental disorder hierarchy")
        
        # Try to use existing hierarchy file
        output_dir = "output"
        hierarchy_files = [f for f in os.listdir(output_dir) if f.startswith("complete_hierarchy_") and f.endswith(".json")]
        
        if hierarchy_files:
            # Use the most recent file
            latest_file = sorted(hierarchy_files)[-1]
            hierarchy_path = os.path.join(output_dir, latest_file)
            print(f"Using existing hierarchy file: {hierarchy_path}")
            
            try:
                with open(hierarchy_path, 'r', encoding='utf-8') as f:
                    hierarchy = json.load(f)
            except Exception as e:
                print(f"Error reading hierarchy file: {e}")
                return
        else:
            print("No existing hierarchy files found")
            return
    
    # Extract F codes
    f_codes = extract_f_codes(hierarchy)
    
    if not f_codes:
        print("No F codes found in the hierarchy")
        return
    
    # Save to Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_file = f"f_codes_{timestamp}.xlsx"
    save_to_excel(f_codes, excel_file)
    
    # Save as JSON for programmatic access
    json_file = os.path.join(OUTPUT_DIR, f"f_codes_{timestamp}.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(f_codes, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON F codes to {json_file}")
    
    # Analyze the F codes
    top_level_f_codes = [code for code in f_codes if len(code.get('codeValue', '')) == 3]
    leaf_nodes = [code for code in f_codes if code.get('isLeafNode', True)]
    parent_nodes = [code for code in f_codes if not code.get('isLeafNode', True)]
    
    print("\nF Code Statistics:")
    print(f"Total F codes: {len(f_codes)}")
    print(f"Top-level F codes (e.g., F00, F01): {len(top_level_f_codes)}")
    print(f"Leaf nodes (end codes): {len(leaf_nodes)}")
    print(f"Parent nodes (categories): {len(parent_nodes)}")
    
    # Print the first few top-level F codes
    if top_level_f_codes:
        print("\nSample top-level F codes:")
        for code in sorted(top_level_f_codes, key=lambda x: x.get('codeValue', ''))[:10]:
            print(f"{code.get('codeValue', '')}: {code.get('nameNorwegian', '')}")

if __name__ == "__main__":
    main()
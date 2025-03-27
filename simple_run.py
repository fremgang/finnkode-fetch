#!/usr/bin/env python
"""
Simple runner script that directly fetches mental disorders from Finnkode.
"""
import os
import sys
import requests
import json
import pandas as pd
from datetime import datetime

# Constants
API_URL = "https://fat.kote.helsedirektoratet.no/api/code-systems/icd10/V/hierarchy"
OUTPUT_DIR = "output"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_mental_disorders():
    """Fetch mental disorder codes from the API."""
    print("Fetching mental disorder codes (F00-F99)...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Origin": "https://finnkode.helsedirektoratet.no",
        "Connection": "keep-alive"
    }
    
    try:
        response = requests.get(API_URL, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("Successfully fetched data")
            return data
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def extract_f_codes(data, f_codes=None):
    """Extract all F codes recursively from the hierarchy."""
    if f_codes is None:
        f_codes = []
    
    # Process this node if it's an F code
    if isinstance(data, dict) and 'codeValue' in data:
        code = data['codeValue']
        if code.startswith('F') and len(code) > 1:  # Ensure it's not just "F" itself
            f_codes.append(data)
    
    # Process children recursively
    if isinstance(data, dict) and 'children' in data and data['children']:
        for child in data['children']:
            extract_f_codes(child, f_codes)
    
    return f_codes

def create_dataframe(f_codes):
    """Convert the F codes to a DataFrame."""
    if not f_codes:
        return pd.DataFrame()
    
    # Extract relevant fields
    rows = []
    for code in f_codes:
        row = {
            'codeValue': code.get('codeValue'),
            'nameNorwegian': code.get('nameNorwegian'),
            'active': code.get('active'),
            'isLeafNode': code.get('isLeafNode'),
            'sortIndex': code.get('sortIndex')
        }
        
        # Add path as a string if available
        if 'path' in code:
            row['path'] = ' > '.join(code['path'])
        
        rows.append(row)
    
    return pd.DataFrame(rows)

def main():
    """Main function."""
    # Fetch data
    data = fetch_mental_disorders()
    
    if not data:
        print("Failed to fetch data. Exiting.")
        return
    
    # Save raw data for inspection
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    raw_filename = os.path.join(OUTPUT_DIR, f"raw_mental_disorders_{timestamp}.json")
    with open(raw_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved raw data to {raw_filename}")
    
    # Extract F codes
    f_codes = extract_f_codes(data)
    print(f"Extracted {len(f_codes)} mental disorder codes")
    
    # Create DataFrame
    df = create_dataframe(f_codes)
    
    # Export to Excel
    excel_filename = os.path.join(OUTPUT_DIR, f"mental_disorders_{timestamp}.xlsx")
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Mental Disorders', index=False)
    print(f"Exported data to {excel_filename}")
    
    # Print statistics
    if not df.empty:
        print("\nStatistics:")
        print(f"Total codes: {len(df)}")
        
        # Count leaf nodes vs parent codes
        leaf_nodes = df[df['isLeafNode'] == True]
        parent_nodes = df[df['isLeafNode'] == False]
        print(f"Leaf nodes (end codes): {len(leaf_nodes)}")
        print(f"Parent nodes (categories): {len(parent_nodes)}")
        
        # Print sample codes
        print("\nSample codes:")
        for _, row in df.head().iterrows():
            print(f"{row['codeValue']}: {row['nameNorwegian']}")

if __name__ == "__main__":
    main()
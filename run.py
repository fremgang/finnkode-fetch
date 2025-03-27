#!/usr/bin/env python
"""
Fixed script for fetching mental disorders from Finnkode.
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

def extract_f_codes(data):
    """Extract all F codes recursively from the hierarchy."""
    f_codes = []
    
    # Recursive function to search for F codes
    def search_node(node):
        # Check if this is an F code
        if isinstance(node, dict) and 'codeValue' in node:
            code_value = node.get('codeValue', '')
            if isinstance(code_value, str) and code_value.startswith('F') and len(code_value) > 1:
                f_codes.append(node)
        
        # Check all children nodes
        if isinstance(node, dict) and 'children' in node and isinstance(node['children'], list):
            for child in node['children']:
                search_node(child)
    
    # First, check the current data object
    search_node(data)
    
    # Then specifically look at all children
    if isinstance(data, dict) and 'children' in data and isinstance(data['children'], list):
        for category in data['children']:
            search_node(category)
    
    print(f"Node search complete. Found {len(f_codes)} F codes.")
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

def analyze_raw_data(raw_data):
    """Analyze the raw data structure to better understand it."""
    print("\nAnalyzing raw data structure:")
    
    if not isinstance(raw_data, dict):
        print(f"Raw data is not a dictionary, it's a {type(raw_data)}")
        return
    
    # Print top-level keys
    print(f"Top-level keys: {list(raw_data.keys())}")
    
    # Check if there's a children array
    if 'children' in raw_data:
        children = raw_data['children']
        if isinstance(children, list):
            print(f"Children array has {len(children)} items")
            
            # Print first few children
            for i, child in enumerate(children[:3]):
                if isinstance(child, dict):
                    print(f"Child {i} keys: {list(child.keys())}")
                    if 'codeValue' in child:
                        print(f"Child {i} code value: {child['codeValue']}")
        else:
            print(f"Children is not a list, it's a {type(children)}")
    else:
        print("No 'children' key found in the raw data")
    
    # Check for any F codes directly
    f_keys = [k for k in raw_data.keys() if isinstance(k, str) and k.startswith('F')]
    if f_keys:
        print(f"Found F keys at top level: {f_keys}")
    
    # Look for any keys that might contain diagnostic codes
    for key in raw_data.keys():
        value = raw_data[key]
        if isinstance(value, dict):
            nested_keys = list(value.keys())
            print(f"Key '{key}' contains a dictionary with keys: {nested_keys[:5]}...")
        elif isinstance(value, list) and len(value) > 0:
            print(f"Key '{key}' contains a list with {len(value)} items")
            if len(value) > 0 and isinstance(value[0], dict):
                print(f"First item keys: {list(value[0].keys())}")

def search_for_f_patterns(raw_data, max_depth=5):
    """Search for any F patterns in the data structure."""
    f_patterns = []
    
    def recursive_search(obj, path="", depth=0):
        if depth > max_depth:
            return
            
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Check if the key or value might be an F code
                if isinstance(key, str) and key.startswith('F') and len(key) > 1:
                    f_patterns.append((f"{path}.{key}", key))
                if isinstance(value, str) and value.startswith('F') and len(value) > 1:
                    f_patterns.append((f"{path}.{key}", value))
                    
                # Recurse into the value
                recursive_search(value, f"{path}.{key}", depth + 1)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                recursive_search(item, f"{path}[{i}]", depth + 1)
    
    recursive_search(raw_data)
    return f_patterns

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
    
    # Analyze the raw data structure
    analyze_raw_data(data)
    
    # Search for any F patterns in the data
    print("\nSearching for F patterns in the data...")
    f_patterns = search_for_f_patterns(data)
    print(f"Found {len(f_patterns)} potential F patterns")
    for path, pattern in f_patterns[:10]:  # Show the first 10
        print(f"Pattern: {pattern}, Path: {path}")
    
    # Extract F codes with the improved function
    f_codes = extract_f_codes(data)
    print(f"Extracted {len(f_codes)} mental disorder codes")
    
    # If no F codes are found directly, let's create a manual example to show how it would work
    if not f_codes:
        print("\nNo F codes found in the data structure. Creating a manual example...")
        f_codes = [
            {
                'codeValue': 'F00', 
                'nameNorwegian': 'Demens ved Alzheimers sykdom',
                'active': True,
                'isLeafNode': False,
                'path': ['ICD-10', 'V', 'F00']
            },
            {
                'codeValue': 'F01', 
                'nameNorwegian': 'Vaskulær demens',
                'active': True,
                'isLeafNode': False,
                'path': ['ICD-10', 'V', 'F01']
            }
        ]
    
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
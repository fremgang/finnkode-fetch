#!/usr/bin/env python
"""
Script to fetch mental disorder F-codes using the 'children' API endpoint.
"""
import os
import requests
import json
import pandas as pd
from datetime import datetime

# Create output directory
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_chapter_v_children():
    """
    Fetch children of Chapter V (Mental disorders) using the children endpoint.
    """
    # This URL directly accesses children of chapter V
    url = "https://fat.kote.helsedirektoratet.no/api/code-systems/icd10/V/children"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Origin": "https://finnkode.helsedirektoratet.no",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    }
    
    print(f"Fetching from URL: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print(f"Success! Received {len(response.text)} bytes")
        return response.json()
    else:
        print(f"Error! Status code: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        return None

def fetch_f_block_children(f_block):
    """
    Fetch children of a specific F-block (e.g., F00-F09).
    
    Args:
        f_block (str): The F-block code (e.g., "F00-F09")
        
    Returns:
        dict: The JSON response or None if request fails
    """
    url = f"https://fat.kote.helsedirektoratet.no/api/code-systems/icd10/{f_block}/children"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "*/*",
        "Origin": "https://finnkode.helsedirektoratet.no"
    }
    
    print(f"Fetching children of {f_block} from URL: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print(f"Success! Received {len(response.text)} bytes")
        return response.json()
    else:
        print(f"Error! Status code: {response.status_code}")
        return None

def explore_and_extract_f_codes(data):
    """
    Explore the data structure and extract F-codes.
    """
    if not data:
        print("No data to explore")
        return []
    
    all_f_codes = []
    
    # Check if data is a list or a dict
    if isinstance(data, list):
        print(f"Data is a list with {len(data)} items")
        
        # Find items with F code values
        for item in data:
            if isinstance(item, dict) and 'codeValue' in item:
                code_value = item.get('codeValue', '')
                if isinstance(code_value, str) and code_value.startswith('F') and len(code_value) > 1:
                    all_f_codes.append(item)
                    
                    # Print first few F-codes for verification
                    if len(all_f_codes) <= 5:
                        print(f"Found F-code: {code_value} - {item.get('nameNorwegian', '')}")
    else:
        print("Data is not a list, checking its structure")
        print(f"Data type: {type(data)}")
        
        if isinstance(data, dict):
            print(f"Top-level keys: {list(data.keys())}")
            
            # Look for children or similar keys that might contain F-codes
            for key in ['children', 'items', 'results']:
                if key in data and isinstance(data[key], list):
                    print(f"Found {len(data[key])} items in '{key}' key")
                    return explore_and_extract_f_codes(data[key])
    
    return all_f_codes

def fetch_all_f_codes():
    """
    Fetch all F-codes by first getting the F-blocks and then fetching each block's children.
    """
    # First, get the main F-blocks (F00-F09, F10-F19, etc.)
    blocks_data = fetch_chapter_v_children()
    
    if not blocks_data:
        print("Failed to fetch F-blocks")
        return []
    
    # Save the blocks data
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    blocks_filename = os.path.join(OUTPUT_DIR, f"f_blocks_{timestamp}.json")
    with open(blocks_filename, 'w', encoding='utf-8') as f:
        json.dump(blocks_data, f, indent=2, ensure_ascii=False)
    print(f"Saved F-blocks data to {blocks_filename}")
    
    # Extract F-blocks from the data
    f_blocks = explore_and_extract_f_codes(blocks_data)
    print(f"Found {len(f_blocks)} F-blocks")
    
    # If we already have detailed F-codes in the blocks data, we can just return them
    if f_blocks and any('children' in block for block in f_blocks):
        print("F-blocks already contain detailed code information")
        return f_blocks
    
    # Otherwise, fetch each block's children to get detailed codes
    all_f_codes = []
    for block in f_blocks:
        block_code = block.get('codeValue', '')
        if block_code:
            print(f"\nFetching children of {block_code} ({block.get('nameNorwegian', '')})")
            block_children = fetch_f_block_children(block_code)
            
            if block_children:
                # Save the block children data
                block_filename = os.path.join(OUTPUT_DIR, f"{block_code.replace('-', '_')}_{timestamp}.json")
                with open(block_filename, 'w', encoding='utf-8') as f:
                    json.dump(block_children, f, indent=2, ensure_ascii=False)
                print(f"Saved {block_code} data to {block_filename}")
                
                # Extract F-codes from this block's children
                block_f_codes = explore_and_extract_f_codes(block_children)
                print(f"Found {len(block_f_codes)} F-codes in {block_code}")
                
                # Add block information to each code
                for code in block_f_codes:
                    code['blockCode'] = block_code
                    code['blockName'] = block.get('nameNorwegian', '')
                
                all_f_codes.extend(block_f_codes)
    
    return all_f_codes

def save_to_excel(f_codes, filename="f_codes.xlsx"):
    """
    Save F-codes to Excel file.
    """
    if not f_codes:
        print("No F-codes to save")
        return
    
    # Convert to DataFrame
    rows = []
    for code in f_codes:
        row = {
            'codeValue': code.get('codeValue', ''),
            'nameNorwegian': code.get('nameNorwegian', ''),
            'active': code.get('active', False),
            'isLeafNode': code.get('isLeafNode', False)
        }
        
        # Add block information if available
        if 'blockCode' in code:
            row['blockCode'] = code['blockCode']
            row['blockName'] = code.get('blockName', '')
        
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Sort by code value
    if 'codeValue' in df.columns:
        df = df.sort_values('codeValue')
    
    # Save to Excel
    output_path = os.path.join(OUTPUT_DIR, filename)
    df.to_excel(output_path, index=False)
    print(f"Saved {len(df)} F-codes to {output_path}")
    
    # Print sample
    print("\nSample F-codes:")
    for _, row in df.head().iterrows():
        print(f"{row['codeValue']}: {row['nameNorwegian']}")

def main():
    """Main function."""
    print("Fetching mental disorder F-codes from Finnkode...")
    
    # Fetch all F-codes
    f_codes = fetch_all_f_codes()
    
    # Save to Excel
    if f_codes:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        save_to_excel(f_codes, f"mental_disorders_{timestamp}.xlsx")
    else:
        print("No F-codes found")

if __name__ == "__main__":
    main()
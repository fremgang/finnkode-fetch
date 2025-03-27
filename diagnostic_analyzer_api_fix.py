#!/usr/bin/env python
"""
Fix for diagnostic analyzer that uses a direct API approach to fetch valid F-codes.
This script targets the specific API endpoints used by Finnkode to fetch 
mental disorder codes and other diagnoses.
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

# API endpoints
DIRECT_API_URL = "https://fat.kote.helsedirektoratet.no/api/code-systems/icd10"

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

def fetch_valid_f_codes():
    """
    Fetch valid F-codes directly from the Finnkode API by getting the children
    of the mental disorders chapter (Chapter V).
    
    Returns:
        list: List of valid F-code objects with details
    """
    print("Directly fetching mental disorder codes from API...")
    
    # First, get the chapter V children
    url = f"{DIRECT_API_URL}/V/children"
    
    try:
        response = requests.get(url, headers=API_HEADERS)
        
        if response.status_code == 200:
            chapter_children = response.json()
            print(f"Successfully fetched {len(chapter_children)} chapter V children")
            
            # Save raw children data for inspection
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            raw_file = os.path.join(OUTPUT_DIR, f"chapter_v_children_{timestamp}.json")
            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(chapter_children, f, ensure_ascii=False, indent=2)
            print(f"Saved raw chapter V children to {raw_file}")
            
            # Extract F codes
            f_codes = []
            f_block_codes = []
            
            for item in chapter_children:
                if isinstance(item, dict) and 'codeValue' in item:
                    code_value = item.get('codeValue', '')
                    if code_value.startswith('F') and '-' in code_value:
                        # This is a block code like F00-F09
                        f_block_codes.append(item)
                        
                        # Also add it to our collection
                        f_codes.append(item)
            
            print(f"Found {len(f_block_codes)} F-code blocks")
            
            # Now fetch each block's children
            all_detailed_codes = []
            
            for block in f_block_codes:
                block_code = block.get('codeValue')
                print(f"Fetching children for block: {block_code}")
                
                block_url = f"{DIRECT_API_URL}/{block_code}/children"
                try:
                    block_response = requests.get(block_url, headers=API_HEADERS)
                    
                    if block_response.status_code == 200:
                        block_children = block_response.json()
                        print(f"  Found {len(block_children)} codes in {block_code}")
                        
                        # Save block children for inspection
                        block_file = os.path.join(OUTPUT_DIR, f"{block_code.replace('-', '_')}_{timestamp}.json")
                        with open(block_file, 'w', encoding='utf-8') as f:
                            json.dump(block_children, f, ensure_ascii=False, indent=2)
                        
                        # Add to our collection
                        all_detailed_codes.extend(block_children)
                        
                        # Recursively fetch children for each detailed code
                        for detailed_code in block_children:
                            if isinstance(detailed_code, dict) and 'codeValue' in detailed_code:
                                detailed_value = detailed_code.get('codeValue')
                                if not detailed_code.get('isLeafNode', True):
                                    # This code has children, fetch them
                                    print(f"  Fetching children for: {detailed_value}")
                                    detail_url = f"{DIRECT_API_URL}/{detailed_value}/children"
                                    
                                    try:
                                        detail_response = requests.get(detail_url, headers=API_HEADERS)
                                        
                                        if detail_response.status_code == 200:
                                            detail_children = detail_response.json()
                                            print(f"    Found {len(detail_children)} children codes for {detailed_value}")
                                            all_detailed_codes.extend(detail_children)
                                        else:
                                            print(f"    Error {detail_response.status_code} fetching children for {detailed_value}")
                                    except Exception as e:
                                        print(f"    Error fetching children for {detailed_value}: {e}")
                    else:
                        print(f"  Error {block_response.status_code} fetching {block_code}")
                except Exception as e:
                    print(f"  Error fetching {block_code}: {e}")
            
            # Combine all codes
            f_codes.extend(all_detailed_codes)
            
            # Remove duplicates
            unique_codes = {}
            for code in f_codes:
                if isinstance(code, dict) and 'codeValue' in code:
                    code_value = code.get('codeValue')
                    unique_codes[code_value] = code
            
            unique_f_codes = list(unique_codes.values())
            print(f"Total unique F codes: {len(unique_f_codes)}")
            
            return unique_f_codes
        else:
            print(f"Error {response.status_code} fetching chapter V children")
            return []
    except Exception as e:
        print(f"Error fetching chapter V children: {e}")
        return []

def extract_code_info(codes):
    """
    Extract key information from code objects.
    
    Args:
        codes (list): List of code objects
        
    Returns:
        pd.DataFrame: DataFrame with extracted information
    """
    if not codes:
        return pd.DataFrame()
    
    rows = []
    
    for code in codes:
        if isinstance(code, dict):
            row = {
                'codeValue': code.get('codeValue', ''),
                'nameNorwegian': code.get('nameNorwegian', ''),
                'active': code.get('active', False),
                'isLeafNode': code.get('isLeafNode', True),
                'sortIndex': code.get('sortIndex', 0)
            }
            rows.append(row)
    
    df = pd.DataFrame(rows)
    return df

def save_to_excel(df, filename):
    """
    Save DataFrame to Excel file.
    
    Args:
        df (pd.DataFrame): DataFrame to save
        filename (str): Output filename
        
    Returns:
        str: Path to the saved file
    """
    if df.empty:
        print("No data to save")
        return None
    
    output_path = os.path.join(OUTPUT_DIR, filename)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='F Codes', index=False)
    
    print(f"Saved data to {output_path}")
    return output_path

def main():
    """Main function."""
    print("Fetching valid F-codes from Finnkode API...")
    
    # Fetch valid F-codes directly from the API
    f_codes = fetch_valid_f_codes()
    
    if not f_codes:
        print("Failed to fetch F-codes")
        return
    
    # Extract information
    df = extract_code_info(f_codes)
    
    if df.empty:
        print("No F-code information extracted")
        return
    
    # Save to Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_file = f"valid_f_codes_{timestamp}.xlsx"
    save_to_excel(df, excel_file)
    
    # Save as JSON for programmatic access
    json_file = os.path.join(OUTPUT_DIR, f"valid_f_codes_{timestamp}.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(f_codes, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON F-codes to {json_file}")
    
    # Print summary statistics
    print("\nF-Code Statistics:")
    print(f"Total codes: {len(df)}")
    print(f"Leaf nodes (end codes): {df['isLeafNode'].sum()}")
    print(f"Parent nodes (categories): {len(df) - df['isLeafNode'].sum()}")
    
    # Print top-level categories
    top_level = df[df['codeValue'].str.contains('-')]
    print("\nTop-level categories:")
    for _, row in top_level.iterrows():
        print(f"{row['codeValue']}: {row['nameNorwegian']}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python
"""
Simple script to fetch mental disorder codes from Finnkode.
This script is self-contained and doesn't require the module structure.
"""
import requests
import json
import os
from datetime import datetime

# Create output directory
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

def get_icd10_mental_disorders():
    """Get all ICD-10 mental disorders (F00-F99)."""
    url = "https://fat.kote.helsedirektoratet.no/api/code-systems/icd10/V/hierarchy"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Origin": "https://finnkode.helsedirektoratet.no",
        "Connection": "keep-alive"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return None
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None

def extract_f_codes_recursive(data, f_codes=None):
    """Recursively extract all F codes from the hierarchy."""
    if f_codes is None:
        f_codes = []
        
    # Check if this is a code starting with F
    if isinstance(data, dict) and 'codeValue' in data:
        code_value = data['codeValue']
        if code_value.startswith('F') and len(code_value) > 1:  # Ensure it's not just "F" itself
            f_codes.append(data)
            
    # Check children recursively
    if isinstance(data, dict) and 'children' in data and data['children']:
        for child in data['children']:
            extract_f_codes_recursive(child, f_codes)
            
    return f_codes

def main():
    """Main function."""
    print("Fetching mental disorder codes (F00-F99)...")
    
    # Fetch data
    hierarchy_data = get_icd10_mental_disorders()
    
    if not hierarchy_data:
        print("Failed to fetch data.")
        return
    
    # Save raw data for inspection
    raw_filename = os.path.join(output_dir, f"raw_mental_disorders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(raw_filename, 'w', encoding='utf-8') as f:
        json.dump(hierarchy_data, f, indent=2, ensure_ascii=False)
    print(f"Saved raw data to {raw_filename}")
    
    # Extract F codes
    f_codes = extract_f_codes_recursive(hierarchy_data)
    print(f"Extracted {len(f_codes)} mental disorder codes")
    
    # Save extracted F codes
    f_codes_filename = os.path.join(output_dir, f"f_codes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(f_codes_filename, 'w', encoding='utf-8') as f:
        json.dump(f_codes, f, indent=2, ensure_ascii=False)
    print(f"Saved extracted F codes to {f_codes_filename}")
    
    # Print some sample codes
    if f_codes:
        print("\nSample codes:")
        for i, code in enumerate(f_codes[:5]):
            print(f"{code.get('codeValue', 'N/A')}: {code.get('nameNorwegian', 'N/A')}")
        
        # Print how many codes start with each F prefix
        f_prefixes = {}
        for code in f_codes:
            code_value = code.get('codeValue', '')
            if code_value.startswith('F') and len(code_value) >= 3:
                prefix = code_value[:3]  # Get F00, F01, etc.
                if prefix in f_prefixes:
                    f_prefixes[prefix] += 1
                else:
                    f_prefixes[prefix] = 1
        
        print("\nCode distribution:")
        for prefix, count in sorted(f_prefixes.items()):
            print(f"{prefix}: {count} codes")

if __name__ == "__main__":
    main()
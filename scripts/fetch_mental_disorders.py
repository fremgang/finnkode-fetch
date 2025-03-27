#!/usr/bin/env python
"""
Example script to fetch and export all ICD-10 mental disorder codes (F00-F99).
"""
import os
import sys
import pandas as pd
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.client import FinnkodeClient
from src.utils.export import create_dataframe_from_mental_disorders, export_to_excel
from src.utils.logger import get_default_logger

def main():
    """Main function to fetch mental disorder codes."""
    # Set up logging
    logger = get_default_logger()
    logger.info("Starting mental disorder code fetch")
    
    # Create API client
    client = FinnkodeClient()
    
    # Fetch mental disorder codes
    logger.info("Fetching mental disorder codes (F00-F99)...")
    f_codes = client.fetch_all_mental_disorder_codes()
    logger.info(f"Fetched {len(f_codes)} mental disorder codes")
    
    # Create DataFrame
    df = create_dataframe_from_mental_disorders(f_codes)
    
    # Create output directory if it doesn't exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Export to Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"mental_disorder_codes_{timestamp}.xlsx"
    export_to_excel({"Mental Disorders (F00-F99)": df}, output_file, output_dir)
    
    # Print a sample of the data
    print("\nSample of mental disorder codes:")
    print(df.head())
    
    # Print some statistics
    if not df.empty:
        print("\nStatistics:")
        print(f"Total codes: {len(df)}")
        
        # Count leaf nodes vs parent codes
        leaf_nodes = df[df['isLeafNode'] == True]
        parent_nodes = df[df['isLeafNode'] == False]
        print(f"Leaf nodes (end codes): {len(leaf_nodes)}")
        print(f"Parent nodes (categories): {len(parent_nodes)}")
        
        # Top-level categories
        if 'path' in df.columns:
            top_levels = df[df['path'].str.count('>') == 1]
            print(f"Top-level categories: {len(top_levels)}")
            
            print("\nTop-level mental disorder categories:")
            for _, row in top_levels.iterrows():
                print(f"{row['codeValue']} - {row['nameNorwegian']}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python
"""
Main script for fetching medical code data from Finnkode.
"""
import os
import sys
import json
import argparse
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.client import FinnkodeClient
from src.utils.export import (
    create_dataframe_from_results, 
    create_dataframe_from_mental_disorders,
    export_to_csv, 
    export_to_excel
)
from src.utils.logger import get_default_logger
from src.models.code_types import CODE_TYPES
from src.config import Config

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Fetch medical code data from Finnkode.')
    
    parser.add_argument('--query', '-q', type=str, default='',
                        help='Search query to filter results')
    
    parser.add_argument('--code-type', '-t', type=str, choices=['icd10', 'icpc2', 'ncmp', 'ncsp', 'ncrp', 'atc'],
                        help='Medical code type to fetch')
    
    parser.add_argument('--category', '-c', type=str,
                        help='Category within the code system (e.g., "V" for mental disorders in ICD-10)')
    
    parser.add_argument('--mental-disorders', '-m', action='store_true',
                        help='Fetch all mental disorders (F00-F99)')
    
    parser.add_argument('--output-format', '-f', type=str, choices=['csv', 'excel'], default='excel',
                        help='Output format (default: excel)')
    
    parser.add_argument('--output-dir', '-o', type=str, default=Config.OUTPUT_DIR,
                        help=f'Output directory (default: {Config.OUTPUT_DIR})')
    
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Enable debug mode with more verbose output')
    
    parser.add_argument('--analyze', action='store_true',
                        help='Analyze API responses to understand the structure')
    
    return parser.parse_args()

def save_api_response(response, filename):
    """Save API response to a file for analysis."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(response, f, indent=2, ensure_ascii=False)
    print(f"Saved API response to {filename}")

def main():
    """Main function."""
    args = parse_arguments()
    
    # Set up logging
    logger = get_default_logger()
    log_level = 'DEBUG' if args.debug else 'INFO'
    logger.setLevel(log_level)
    logger.info("Starting Finnkode data fetcher")
    
    # Create API client
    client = FinnkodeClient()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # If analyze flag is set, save raw API responses for analysis
    if args.analyze:
        # Analyze different API endpoints
        logger.info("Analyzing API responses...")
        
        # Test search API
        test_search = client.search("diabetes")
        if test_search:
            save_api_response(
                test_search, 
                os.path.join(args.output_dir, f"api_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            )
        
        # Test hierarchy API for ICD-10
        test_hierarchy = client.get_icd10_chapter_list()
        if test_hierarchy:
            save_api_response(
                test_hierarchy, 
                os.path.join(args.output_dir, f"api_icd10_chapters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            )
        
        # Test mental disorders hierarchy
        test_mental = client.get_icd10_mental_disorders()
        if test_mental:
            save_api_response(
                test_mental, 
                os.path.join(args.output_dir, f"api_mental_disorders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            )
        
        # Exit after analysis
        return
    
    # Fetch mental disorders (F codes)
    if args.mental_disorders:
        logger.info("Fetching mental disorder codes (F00-F99)...")
        
        f_codes = client.fetch_all_mental_disorder_codes()
        logger.info(f"Fetched {len(f_codes)} mental disorder codes")
        
        # Create DataFrame
        df = create_dataframe_from_mental_disorders(f_codes)
        
        # Export results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if args.output_format == 'csv':
            output_file = f"mental_disorder_codes_{timestamp}.csv"
            export_to_csv(df, output_file, args.output_dir)
        else:
            output_file = f"mental_disorder_codes_{timestamp}.xlsx"
            export_to_excel({"Mental Disorders (F00-F99)": df}, output_file, args.output_dir)
    
    # Fetch codes by type and category
    elif args.code_type and args.category:
        logger.info(f"Fetching {args.code_type.upper()} codes for category {args.category}...")
        
        hierarchy_data = client.get_code_system_hierarchy(args.code_type, args.category)
        
        if hierarchy_data:
            # Save raw hierarchy data for reference
            raw_filename = os.path.join(
                args.output_dir, 
                f"{args.code_type}_{args.category}_hierarchy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            save_api_response(hierarchy_data, raw_filename)
            
            # Create DataFrame
            if args.code_type == 'icd10' and args.category == 'V':
                # Special handling for mental disorders
                f_codes = client.extract_mental_disorder_codes(hierarchy_data)
                df = create_dataframe_from_mental_disorders(f_codes)
                logger.info(f"Extracted {len(f_codes)} mental disorder codes")
            else:
                # Generic handling for other categories
                df = pd.DataFrame()
                logger.info("No specific extraction logic for this category")
            
            # Export results if we have data
            if not df.empty:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                if args.output_format == 'csv':
                    output_file = f"{args.code_type}_{args.category}_codes_{timestamp}.csv"
                    export_to_csv(df, output_file, args.output_dir)
                else:
                    output_file = f"{args.code_type}_{args.category}_codes_{timestamp}.xlsx"
                    export_to_excel({f"{args.code_type.upper()} {args.category}": df}, output_file, args.output_dir)
        else:
            logger.error(f"Failed to fetch hierarchy data for {args.code_type} {args.category}")
    
    # Fetch chapters for a code system
    elif args.code_type:
        logger.info(f"Fetching chapters for {args.code_type.upper()}...")
        
        if args.code_type == 'icd10':
            chapters = client.get_icd10_chapter_list()
            
            if chapters:
                # Save raw chapter data
                raw_filename = os.path.join(
                    args.output_dir, 
                    f"{args.code_type}_chapters_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                save_api_response(chapters, raw_filename)
                
                # Create DataFrame from chapter data
                if 'children' in chapters:
                    chapter_rows = []
                    for chapter in chapters['children']:
                        chapter_rows.append({
                            'codeValue': chapter.get('codeValue'),
                            'nameNorwegian': chapter.get('nameNorwegian'),
                            'active': chapter.get('active'),
                            'isLeafNode': chapter.get('isLeafNode'),
                            'sortIndex': chapter.get('sortIndex')
                        })
                    
                    df = pd.DataFrame(chapter_rows)
                    logger.info(f"Found {len(df)} chapters for {args.code_type.upper()}")
                    
                    # Export results
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    if args.output_format == 'csv':
                        output_file = f"{args.code_type}_chapters_{timestamp}.csv"
                        export_to_csv(df, output_file, args.output_dir)
                    else:
                        output_file = f"{args.code_type}_chapters_{timestamp}.xlsx"
                        export_to_excel({f"{args.code_type.upper()} Chapters": df}, output_file, args.output_dir)
                else:
                    logger.error("No chapters found in the response")
            else:
                logger.error(f"Failed to fetch chapters for {args.code_type}")
        else:
            logger.error(f"Chapter fetching not implemented for {args.code_type}")
    
    # Simple search (fallback)
    elif args.query:
        logger.info(f"Searching for: '{args.query}'")
        
        results = client.search(args.query)
        
        if results and 'results' in results:
            df = create_dataframe_from_results(results['results'])
            logger.info(f"Found {len(df)} results for '{args.query}'")
            
            if not df.empty:
                # Export results
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                if args.output_format == 'csv':
                    output_file = f"search_{args.query.replace(' ', '_')}_{timestamp}.csv"
                    export_to_csv(df, output_file, args.output_dir)
                else:
                    output_file = f"search_{args.query.replace(' ', '_')}_{timestamp}.xlsx"
                    export_to_excel({f"Search: {args.query}": df}, output_file, args.output_dir)
        else:
            logger.error("No results found or API error occurred")
    
    else:
        logger.info("No action specified. Use -h for help.")
        parser = argparse.ArgumentParser()
        parser.print_help()

if __name__ == "__main__":
    main()
#!/usr/bin/env python
"""
Script to create visualizations of mental disorder codes.
"""
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.client import FinnkodeClient
from src.utils.export import create_dataframe_from_mental_disorders
from src.utils.logger import get_default_logger

def create_hierarchical_visualization(f_codes, output_dir):
    """
    Create a hierarchical visualization of mental disorder codes.
    
    Args:
        f_codes (list): List of mental disorder codes
        output_dir (str): Output directory for visualizations
    """
    # Count codes at each level
    level_counts = {}
    
    for code in f_codes:
        if 'path' in code:
            level = len(code['path'])
            if level in level_counts:
                level_counts[level] += 1
            else:
                level_counts[level] = 1
    
    # Create visualization
    plt.figure(figsize=(10, 6))
    sns.barplot(x=list(level_counts.keys()), y=list(level_counts.values()))
    plt.title('Mental Disorder Codes by Hierarchy Level')
    plt.xlabel('Hierarchy Level')
    plt.ylabel('Number of Codes')
    plt.tight_layout()
    
    # Save visualization
    output_file = os.path.join(output_dir, f"mental_disorders_hierarchy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    plt.savefig(output_file)
    print(f"Saved hierarchy visualization to {output_file}")
    plt.close()

def create_top_categories_visualization(f_codes, output_dir):
    """
    Create a visualization of top-level mental disorder categories.
    
    Args:
        f_codes (list): List of mental disorder codes
        output_dir (str): Output directory for visualizations
    """
    # Identify top-level categories
    top_categories = {}
    
    for code in f_codes:
        if 'codeValue' in code and code['codeValue'].startswith('F') and len(code['codeValue']) == 3:
            # This assumes F00-F99 pattern for top categories
            top_categories[code['codeValue']] = code.get('nameNorwegian', code['codeValue'])
    
    # Count codes within each top category
    category_counts = {}
    
    for code in f_codes:
        if 'codeValue' in code and code['codeValue'].startswith('F') and len(code['codeValue']) > 1:
            # Extract the first 3 characters (e.g., F00, F01, etc.)
            top_cat = code['codeValue'][:3]
            if top_cat in category_counts:
                category_counts[top_cat] += 1
            else:
                category_counts[top_cat] = 1
    
    # Sort by code
    sorted_categories = sorted(category_counts.items())
    
    # Create visualization
    plt.figure(figsize=(15, 8))
    
    # Get category codes and counts
    cat_codes = [cat[0] for cat in sorted_categories]
    cat_counts = [cat[1] for cat in sorted_categories]
    
    # Create bar plot
    bars = plt.bar(cat_codes, cat_counts)
    
    # Add category names as labels
    plt.xticks(rotation=90)
    plt.title('Number of Mental Disorder Codes by Top-Level Category')
    plt.xlabel('Category')
    plt.ylabel('Number of Codes')
    plt.tight_layout()
    
    # Save visualization
    output_file = os.path.join(output_dir, f"mental_disorders_categories_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    plt.savefig(output_file)
    print(f"Saved categories visualization to {output_file}")
    plt.close()
    
    # Create a more detailed visualization with category names
    plt.figure(figsize=(15, 10))
    
    # Prepare data for plotting
    cat_names = []
    for code in cat_codes:
        if code in top_categories:
            # Truncate name if too long
            name = top_categories[code]
            if len(name) > 40:
                name = name[:37] + "..."
            cat_names.append(f"{code}: {name}")
        else:
            cat_names.append(code)
    
    # Create horizontal bar plot for better readability of labels
    plt.barh(cat_names, cat_counts)
    plt.title('Mental Disorder Categories')
    plt.xlabel('Number of Codes')
    plt.tight_layout()
    
    # Save visualization
    output_file = os.path.join(output_dir, f"mental_disorders_categories_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    plt.savefig(output_file)
    print(f"Saved detailed categories visualization to {output_file}")
    plt.close()

def create_treemap(f_codes, output_dir):
    """
    Create a treemap visualization of mental disorder codes.
    Uses matplotlib's nested pie charts as a treemap alternative.
    
    Args:
        f_codes (list): List of mental disorder codes
        output_dir (str): Output directory for visualizations
    """
    try:
        import squarify
        
        # Group codes by top-level category
        categories = {}
        
        for code in f_codes:
            if 'codeValue' in code and code['codeValue'].startswith('F') and len(code['codeValue']) > 1:
                # Extract the first 3 characters (e.g., F00, F01, etc.)
                top_cat = code['codeValue'][:3]
                if top_cat in categories:
                    categories[top_cat].append(code)
                else:
                    categories[top_cat] = [code]
        
        # Prepare data for treemap
        sizes = [len(categories[cat]) for cat in categories]
        labels = [f"{cat} ({len(categories[cat])})" for cat in categories]
        
        # Create treemap
        plt.figure(figsize=(16, 10))
        squarify.plot(sizes=sizes, label=labels, alpha=0.8)
        plt.axis('off')
        plt.title('Mental Disorder Codes Treemap')
        
        # Save visualization
        output_file = os.path.join(output_dir, f"mental_disorders_treemap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        plt.savefig(output_file, bbox_inches='tight')
        print(f"Saved treemap visualization to {output_file}")
        plt.close()
    except ImportError:
        print("squarify package not found. Skipping treemap visualization.")
        print("Install with: pip install squarify")

def main():
    """Main function to create visualizations of mental disorder codes."""
    # Set up logging
    logger = get_default_logger()
    logger.info("Starting mental disorder visualization")
    
    # Create API client
    client = FinnkodeClient()
    
    # Fetch mental disorder codes
    logger.info("Fetching mental disorder codes (F00-F99)...")
    f_codes = client.fetch_all_mental_disorder_codes()
    logger.info(f"Fetched {len(f_codes)} mental disorder codes")
    
    # Create output directory if it doesn't exist
    output_dir = "visualizations"
    os.makedirs(output_dir, exist_ok=True)
    
    # Create visualizations
    logger.info("Creating visualizations...")
    
    # Create hierarchical visualization
    create_hierarchical_visualization(f_codes, output_dir)
    
    # Create top categories visualization
    create_top_categories_visualization(f_codes, output_dir)
    
    # Create treemap visualization
    create_treemap(f_codes, output_dir)
    
    # Save the raw data for reference
    raw_file = os.path.join(output_dir, f"mental_disorders_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(f_codes, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved raw data to {raw_file}")
    
    logger.info("Visualization complete. Check the 'visualizations' directory for output files.")

if __name__ == "__main__":
    main()
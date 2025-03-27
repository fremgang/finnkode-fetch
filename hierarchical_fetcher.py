#!/usr/bin/env python
"""
Enhanced script for fetching complete hierarchical diagnostic codes from Finnkode.
This script fetches all levels of diagnoses and subdiagnoses for better visualization.
"""
import os
import sys
import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from tqdm import tqdm
import argparse
import networkx as nx
from concurrent.futures import ThreadPoolExecutor, as_completed

# Constants
BASE_API_URL = "https://fat.kote.helsedirektoratet.no/api/code-systems/icd10"
CHILDREN_API_ENDPOINT = "children"
HIERARCHY_API_ENDPOINT = "hierarchy"
OUTPUT_DIR = "output"
VISUALIZATIONS_DIR = "visualizations"

# Create output directories
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(VISUALIZATIONS_DIR, exist_ok=True)

# Set up request headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Origin": "https://finnkode.helsedirektoratet.no",
    "Connection": "keep-alive"
}

def fetch_api_data(url):
    """
    Fetch data from the API with proper error handling.
    
    Args:
        url (str): API URL to fetch data from
        
    Returns:
        dict: JSON response or None if failed
    """
    try:
        response = requests.get(url, headers=HEADERS)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code} for URL: {url}")
            print(response.text[:200] + "..." if len(response.text) > 200 else response.text)
            return None
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return None

def fetch_chapter_v_hierarchy():
    """
    Fetch the complete hierarchy for Chapter V (Mental disorders).
    
    Returns:
        dict: Hierarchy data or None if failed
    """
    url = f"{BASE_API_URL}/V/{HIERARCHY_API_ENDPOINT}"
    print(f"Fetching Chapter V hierarchy from: {url}")
    return fetch_api_data(url)

def fetch_code_children(code):
    """
    Fetch children for a specific code.
    
    Args:
        code (str): The code to fetch children for
        
    Returns:
        list: List of children or None if failed
    """
    url = f"{BASE_API_URL}/{code}/{CHILDREN_API_ENDPOINT}"
    data = fetch_api_data(url)
    return data

def fetch_detailed_code_info(code):
    """
    Fetch detailed information for a specific code.
    
    Args:
        code (str): The code to fetch details for
        
    Returns:
        dict: Code details or None if failed
    """
    url = f"{BASE_API_URL}/{code}"
    return fetch_api_data(url)

def build_complete_hierarchy(max_depth=5, batch_size=10, parent_code="V"):
    """
    Build a complete hierarchy of codes by recursively fetching children.
    
    Args:
        max_depth (int): Maximum depth to fetch
        batch_size (int): Size of concurrent fetching batches
        parent_code (str): Starting code (default is "V" for mental disorders)
        
    Returns:
        dict: Complete hierarchy
    """
    print(f"Building complete hierarchy starting from {parent_code} (max depth: {max_depth})")
    
    # Start with the parent hierarchy
    if parent_code == "V":
        hierarchy = fetch_chapter_v_hierarchy()
    else:
        hierarchy = {"codeValue": parent_code, "children": []}
        children = fetch_code_children(parent_code)
        if children:
            hierarchy["children"] = children
    
    if not hierarchy:
        print("Failed to fetch initial hierarchy")
        return None
        
    # Function to fetch children concurrently for a batch of nodes
    def fetch_batch(nodes, depth):
        valid_nodes = []
        valid_indices = []
        
        # First, filter out nodes that are not dictionaries or don't need children
        for i, node in enumerate(nodes):
            if isinstance(node, dict) and 'codeValue' in node:
                if (not node.get('children') and not node.get('isLeafNode', False) and 
                    node.get('codeValue') and node.get('codeValue') != "V"):
                    valid_nodes.append(node)
                    valid_indices.append(i)
        
        if not valid_nodes:
            return
        
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = []
            for node in valid_nodes:
                code = node.get('codeValue')
                futures.append(executor.submit(fetch_code_children, code))
            
            # Process results
            for i, future in enumerate(as_completed(futures)):
                children = future.result()
                if children:
                    valid_nodes[i]['children'] = children
                    if len(children) > 0:
                        valid_nodes[i]['isLeafNode'] = False
    
    # Process the hierarchy level by level with progress bar
    def process_level_by_level():
        current_level = [hierarchy]
        for depth in range(max_depth):
            if not current_level:
                break
                
            print(f"Processing depth {depth+1}/{max_depth} ({len(current_level)} nodes)")
            
            # Split into batches for concurrent processing
            for i in range(0, len(current_level), batch_size):
                batch = current_level[i:i+batch_size]
                fetch_batch(batch, depth)
            
            # Prepare next level
            next_level = []
            for node in current_level:
                if isinstance(node, dict) and 'children' in node and node['children']:
                    next_level.extend(node['children'])
            
            current_level = next_level
    
    # Use level-by-level processing for better parallelization
    process_level_by_level()
    
    return hierarchy

def extract_all_codes(hierarchy, code_list=None, parent=None, depth=0):
    """
    Extract all codes from the hierarchy into a flat list with parent relationships.
    
    Args:
        hierarchy (dict): Hierarchy data
        code_list (list, optional): List to store codes
        parent (dict, optional): Parent node
        depth (int): Current depth in the hierarchy
        
    Returns:
        list: Flat list of all codes with parent info
    """
    if code_list is None:
        code_list = []
    
    if not hierarchy:
        return code_list
    
    # Skip if this isn't a proper code node
    if not isinstance(hierarchy, dict) or 'codeValue' not in hierarchy:
        return code_list
    
    # Create a copy of the node with additional info
    node = {k: v for k, v in hierarchy.items() if k != 'children'}
    
    # Add parent info and depth
    if parent:
        node['parentCode'] = parent.get('codeValue')
        node['parentName'] = parent.get('nameNorwegian')
    
    node['depth'] = depth
    code_list.append(node)
    
    # Process children
    if 'children' in hierarchy and hierarchy['children']:
        for child in hierarchy['children']:
            extract_all_codes(child, code_list, hierarchy, depth + 1)
    
    return code_list

def create_hierarchy_dataframe(code_list):
    """
    Convert the code list into a DataFrame with hierarchical structure.
    
    Args:
        code_list (list): List of code dictionaries
        
    Returns:
        pandas.DataFrame: DataFrame with hierarchical structure
    """
    if not code_list:
        return pd.DataFrame()
    
    # Create DataFrame
    df = pd.DataFrame(code_list)
    
    # Sort by code value for better organization
    if 'codeValue' in df.columns:
        df = df.sort_values('codeValue')
    
    return df

def visualize_hierarchy_network(code_df, output_file=None, max_nodes=500):
    """
    Create a network visualization of the code hierarchy.
    
    Args:
        code_df (pandas.DataFrame): DataFrame with code hierarchy
        output_file (str, optional): Output file path
        max_nodes (int): Maximum number of nodes to display
        
    Returns:
        str: Path to the created visualization
    """
    # Create a graph
    G = nx.DiGraph()
    
    # Limit the number of nodes if needed
    if len(code_df) > max_nodes:
        print(f"Limiting visualization to {max_nodes} nodes (out of {len(code_df)})")
        # Prioritize higher-level nodes (lower depth)
        if 'depth' in code_df.columns:
            df_subset = code_df.sort_values('depth').head(max_nodes)
        else:
            df_subset = code_df.head(max_nodes)
    else:
        df_subset = code_df
    
    # Add nodes
    for _, row in df_subset.iterrows():
        code = row['codeValue']
        name = row.get('nameNorwegian', '')
        G.add_node(code, name=name)
        
        # Add edge to parent
        if 'parentCode' in row and pd.notna(row['parentCode']):
            parent = row['parentCode']
            if parent in df_subset['codeValue'].values:
                G.add_edge(parent, code)
    
    # Create visualization
    plt.figure(figsize=(20, 15))
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_size=100, alpha=0.8, 
                          node_color=[0.8, 0.3, 0.3] if 'F' in df_subset['codeValue'].iloc[0] else [0.3, 0.3, 0.8])
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, alpha=0.3, arrows=True, arrowsize=15)
    
    # Draw labels for higher-level nodes (limit to avoid clutter)
    labels = {node: node for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=8)
    
    plt.title('Diagnostic Code Hierarchy Network')
    plt.axis('off')
    
    # Save the visualization
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(VISUALIZATIONS_DIR, f"code_network_{timestamp}.png")
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Saved network visualization to {output_file}")
    return output_file

def visualize_hierarchical_treemap(code_df, output_file=None):
    """
    Create a treemap visualization of the code hierarchy.
    
    Args:
        code_df (pandas.DataFrame): DataFrame with code hierarchy
        output_file (str, optional): Output file path
        
    Returns:
        str: Path to the created visualization
    """
    try:
        import squarify
        
        # Count codes by block (first 3 characters, e.g., F00, F01)
        blocks = {}
        
        for _, row in code_df.iterrows():
            code = row['codeValue']
            if code.startswith('F') and len(code) >= 3:
                block = code[:3]
                if block in blocks:
                    blocks[block] += 1
                else:
                    blocks[block] = 1
        
        # Prepare data for treemap
        sizes = [blocks[block] for block in blocks]
        labels = [f"{block} ({blocks[block]})" for block in blocks]
        
        # Create treemap
        plt.figure(figsize=(16, 10))
        norm = plt.Normalize(0, len(blocks))
        colors = plt.cm.viridis(norm(range(len(blocks))))
        squarify.plot(sizes=sizes, label=labels, alpha=0.8, color=colors)
        plt.axis('off')
        plt.title('Diagnostic Codes by Block')
        
        # Save visualization
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(VISUALIZATIONS_DIR, f"code_treemap_{timestamp}.png")
        
        plt.savefig(output_file, bbox_inches='tight')
        plt.close()
        
        print(f"Saved treemap visualization to {output_file}")
        return output_file
    except ImportError:
        print("squarify package not found. Skipping treemap visualization.")
        print("Install with: pip install squarify")
        return None

def visualize_depth_distribution(code_df, output_file=None):
    """
    Visualize the distribution of codes by hierarchy depth.
    
    Args:
        code_df (pandas.DataFrame): DataFrame with code hierarchy
        output_file (str, optional): Output file path
        
    Returns:
        str: Path to the created visualization
    """
    if 'depth' not in code_df.columns:
        print("Depth information not available in the DataFrame")
        return None
    
    # Group by depth
    depth_counts = code_df['depth'].value_counts().sort_index()
    
    # Create visualization
    plt.figure(figsize=(12, 8))
    ax = sns.barplot(x=depth_counts.index, y=depth_counts.values)
    
    # Add count labels
    for i, v in enumerate(depth_counts.values):
        ax.text(i, v + 5, str(v), ha='center')
    
    plt.title('Distribution of Diagnostic Codes by Hierarchy Depth')
    plt.xlabel('Hierarchy Depth')
    plt.ylabel('Number of Codes')
    plt.xticks(range(len(depth_counts.index)), depth_counts.index)
    
    # Save visualization
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(VISUALIZATIONS_DIR, f"depth_distribution_{timestamp}.png")
    
    plt.savefig(output_file, bbox_inches='tight')
    plt.close()
    
    print(f"Saved depth distribution visualization to {output_file}")
    return output_file

def generate_sunburst_data(hierarchy):
    """
    Generate data for a sunburst chart visualization.
    
    Args:
        hierarchy (dict): Hierarchical data
        
    Returns:
        dict: Data formatted for sunburst visualization
    """
    # This generates data in a format that can be used with D3.js for a sunburst chart
    def process_node(node, parent_id=None):
        if not node or not isinstance(node, dict) or 'codeValue' not in node:
            return None
            
        current = {
            'id': node['codeValue'],
            'name': node.get('nameNorwegian', node['codeValue']),
            'value': 1,  # Base value
            'children': []
        }
        
        if parent_id:
            current['parent'] = parent_id
            
        # Process children
        if 'children' in node and node['children']:
            for child in node['children']:
                child_data = process_node(child, node['codeValue'])
                if child_data:
                    current['children'].append(child_data)
        
        return current
    
    return process_node(hierarchy)

def export_hierarchy_json(hierarchy, output_file=None):
    """
    Export the hierarchy to a JSON file suitable for visualization.
    
    Args:
        hierarchy (dict): Hierarchy data
        output_file (str, optional): Output file path
        
    Returns:
        str: Path to the created file
    """
    # Generate the sunburst data
    sunburst_data = generate_sunburst_data(hierarchy)
    
    # Create output file path
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(OUTPUT_DIR, f"hierarchy_visualization_{timestamp}.json")
    
    # Save to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sunburst_data, f, ensure_ascii=False, indent=2)
    
    print(f"Exported hierarchy visualization data to {output_file}")
    return output_file

def export_to_excel(df, sheet_name="Diagnostic Codes", output_file=None):
    """
    Export the DataFrame to an Excel file.
    
    Args:
        df (pandas.DataFrame): DataFrame to export
        sheet_name (str): Name of the Excel sheet
        output_file (str, optional): Output file path
        
    Returns:
        str: Path to the created file
    """
    if df.empty:
        print("No data to export")
        return None
    
    # Create output file path
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(OUTPUT_DIR, f"diagnostic_codes_{timestamp}.xlsx")
    
    # Export to Excel
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    print(f"Exported {len(df)} diagnostic codes to {output_file}")
    return output_file

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Fetch and visualize hierarchical diagnostic codes.')
    
    parser.add_argument('--code', '-c', type=str, default='V',
                        help='Starting code for hierarchy fetching (default: V for mental disorders)')
    
    parser.add_argument('--depth', '-d', type=int, default=5,
                        help='Maximum depth to fetch in the hierarchy (default: 5)')
    
    parser.add_argument('--batch', '-b', type=int, default=10,
                        help='Batch size for concurrent API requests (default: 10)')
    
    parser.add_argument('--output-dir', '-o', type=str, default=OUTPUT_DIR,
                        help=f'Output directory (default: {OUTPUT_DIR})')
    
    parser.add_argument('--viz-dir', '-v', type=str, default=VISUALIZATIONS_DIR,
                        help=f'Visualizations directory (default: {VISUALIZATIONS_DIR})')
    
    parser.add_argument('--specific-code', '-s', type=str,
                        help='Fetch information for a specific code only')
    
    parser.add_argument('--visualize-only', action='store_true',
                        help='Only create visualizations from existing data')
    
    parser.add_argument('--no-visualize', action='store_true',
                        help='Skip visualization creation')
    
    return parser.parse_args()

def main():
    """Main function."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Update output directories
    global OUTPUT_DIR, VISUALIZATIONS_DIR
    OUTPUT_DIR = args.output_dir
    VISUALIZATIONS_DIR = args.viz_dir
    
    # Create directories if they don't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(VISUALIZATIONS_DIR, exist_ok=True)
    
    # Handle specific code fetching
    if args.specific_code:
        print(f"Fetching detailed information for code: {args.specific_code}")
        code_info = fetch_detailed_code_info(args.specific_code)
        
        if code_info:
            # Save the code info
            code_filename = os.path.join(OUTPUT_DIR, f"{args.specific_code}_details.json")
            with open(code_filename, 'w', encoding='utf-8') as f:
                json.dump(code_info, f, ensure_ascii=False, indent=2)
            print(f"Saved code details to {code_filename}")
            
            # Fetch children
            children = fetch_code_children(args.specific_code)
            if children:
                children_filename = os.path.join(OUTPUT_DIR, f"{args.specific_code}_children.json")
                with open(children_filename, 'w', encoding='utf-8') as f:
                    json.dump(children, f, ensure_ascii=False, indent=2)
                print(f"Saved {len(children)} children to {children_filename}")
            else:
                print(f"No children found for {args.specific_code}")
        else:
            print(f"Failed to fetch information for {args.specific_code}")
        
        return
    
    # Skip fetching if visualize-only is specified
    if args.visualize_only:
        print("Skipping data fetching, using existing data for visualization")
        # Look for the most recent hierarchy file
        hierarchy_files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith('complete_hierarchy_') and f.endswith('.json')]
        if not hierarchy_files:
            print("No existing hierarchy files found. Please run without --visualize-only first.")
            return
            
        # Use the most recent file
        latest_file = sorted(hierarchy_files)[-1]
        hierarchy_path = os.path.join(OUTPUT_DIR, latest_file)
        print(f"Using existing hierarchy from {hierarchy_path}")
        
        with open(hierarchy_path, 'r', encoding='utf-8') as f:
            hierarchy = json.load(f)
    else:
        # Build the complete hierarchy
        print(f"Fetching complete hierarchy starting from {args.code} with max depth {args.depth}")
        start_time = datetime.now()
        hierarchy = build_complete_hierarchy(max_depth=args.depth, batch_size=args.batch, parent_code=args.code)
        end_time = datetime.now()
        print(f"Hierarchy fetching completed in {(end_time - start_time).total_seconds():.2f} seconds")
        
        if not hierarchy:
            print("Failed to build hierarchy. Exiting.")
            return
        
        # Save the complete hierarchy
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        hierarchy_filename = os.path.join(OUTPUT_DIR, f"complete_hierarchy_{timestamp}.json")
        with open(hierarchy_filename, 'w', encoding='utf-8') as f:
            json.dump(hierarchy, f, ensure_ascii=False, indent=2)
        print(f"Saved complete hierarchy to {hierarchy_filename}")
    
    # Extract all codes into a flat list
    all_codes = extract_all_codes(hierarchy)
    print(f"Extracted {len(all_codes)} codes from the hierarchy")
    
    # Create DataFrame
    codes_df = create_hierarchy_dataframe(all_codes)
    
    # Export to Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    excel_filename = os.path.join(OUTPUT_DIR, f"complete_diagnostic_codes_{timestamp}.xlsx")
    export_to_excel(codes_df, "Diagnostic Codes", excel_filename)
    
    # Skip visualization if specified
    if args.no_visualize:
        print("Skipping visualization creation as requested")
        return
    
    # Create visualizations
    print("Creating visualizations...")
    
    # Network visualization
    visualize_hierarchy_network(codes_df)
    
    # Treemap visualization
    visualize_hierarchical_treemap(codes_df)
    
    # Depth distribution
    visualize_depth_distribution(codes_df)
    
    # Export JSON for interactive visualization
    export_hierarchy_json(hierarchy)
    
    print("All operations completed successfully!")

if __name__ == "__main__":
    main()
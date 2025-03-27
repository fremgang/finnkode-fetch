#!/usr/bin/env python
"""
Advanced diagnostic code analyzer for exploring relationships between diagnoses.
This script analyzes ICD-10 codes, extracts relationships, and identifies related conditions.
"""
import os
import sys
import json
import pandas as pd
import requests
import argparse
import matplotlib.pyplot as plt
from datetime import datetime
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Constants
BASE_API_URL = "https://fat.kote.helsedirektoratet.no/api/code-systems/icd10"
SEARCH_API_URL = "https://fs-elastic-prod.ent.westeurope.azure.elastic-cloud.com/api/as/v1/engines/ehelse-kodeverk-prod/search.json"
OUTPUT_DIR = "analysis_output"

# Set up headers
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Origin": "https://finnkode.helsedirektoratet.no",
    "Connection": "keep-alive"
}

SEARCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "authorization": "Bearer search-osdi3rea1ywr1tzff78z75ti",  # Public token used by Finnkode
    "content-type": "application/json",
    "Origin": "https://finnkode.helsedirektoratet.no",
    "Connection": "keep-alive"
}

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

class DiagnosticAnalyzer:
    """Class for analyzing diagnostic codes and their relationships."""
    
    def __init__(self, code_data=None):
        """
        Initialize the analyzer.
        
        Args:
            code_data (dict, optional): Pre-loaded code data
        """
        self.code_data = code_data or {}
        self.code_descriptions = {}
        self.all_codes = set()
    
    def fetch_code_details(self, code):
        """
        Fetch detailed information for a specific code.
        
        Args:
            code (str): The code to fetch details for
            
        Returns:
            dict: Code details or None if failed
        """
        if code in self.code_data:
            return self.code_data[code]
        
        url = f"{BASE_API_URL}/{code}"
        try:
            response = requests.get(url, headers=API_HEADERS)
            
            if response.status_code == 200:
                data = response.json()
                self.code_data[code] = data
                return data
            else:
                print(f"Error {response.status_code} fetching {code}")
                return None
        except Exception as e:
            print(f"Error fetching {code}: {e}")
            return None
    
    def search_codes(self, query, page=1, per_page=50):
        """
        Search for codes using the search API.
        
        Args:
            query (str): Search query
            page (int): Page number
            per_page (int): Results per page
            
        Returns:
            list: Search results
        """
        payload = {
            "query": query,
            "page": {
                "size": per_page,
                "current": page
            },
            "filters": {
                "all": [
                    {
                        "oid_system": "icd10"
                    }
                ]
            }
        }
        
        try:
            response = requests.post(SEARCH_API_URL, headers=SEARCH_HEADERS, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            else:
                print(f"Search error {response.status_code}")
                return []
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def extract_related_codes_from_text(self, text):
        """
        Extract related code references from text.
        
        Args:
            text (str): Text to extract from
            
        Returns:
            list: List of related code references
        """
        if not text:
            return []
        
        # Find ICD-10 code patterns (e.g., F20.0, F31, Z73)
        pattern = r'\b([A-Z]\d{2}(?:\.\d+)?)\b'
        return re.findall(pattern, text)
    
    def analyze_code_relationships(self, codes):
        """
        Analyze relationships between a list of codes.
        
        Args:
            codes (list): List of codes to analyze
            
        Returns:
            dict: Dictionary of relationships between codes
        """
        print(f"Analyzing relationships among {len(codes)} codes...")
        
        # Create a progress bar
        progress = tqdm(total=len(codes), desc="Analyzing codes")
        
        # Dictionary to store relationships
        relationships = {}
        
        # Fetch details for all codes
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit tasks
            future_to_code = {executor.submit(self.fetch_code_details, code): code for code in codes}
            
            # Process results
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    data = future.result()
                    if data:
                        # Extract code description
                        self.code_descriptions[code] = data.get('nameNorwegian', '')
                        
                        # Find related codes in description or other fields
                        description = data.get('nameNorwegian', '')
                        includes = data.get('includes', '')
                        excludes = data.get('excludes', '')
                        
                        # Combine text fields
                        all_text = f"{description} {includes} {excludes}"
                        
                        # Extract related codes
                        related_codes = set(self.extract_related_codes_from_text(all_text))
                        related_codes.discard(code)  # Remove self-reference
                        
                        # Store relationships
                        relationships[code] = list(related_codes)
                        
                        # Add to all codes
                        self.all_codes.add(code)
                        self.all_codes.update(related_codes)
                except Exception as e:
                    print(f"Error analyzing {code}: {e}")
                
                # Update progress
                progress.update(1)
        
        # Close progress bar
        progress.close()
        
        print(f"Relationship analysis complete. Found relationships for {len(relationships)} codes.")
        return relationships
    
    def find_related_diagnoses(self, code, relationships, max_distance=2):
        """
        Find diagnoses related to a specific code within a certain distance.
        
        Args:
            code (str): The code to find related diagnoses for
            relationships (dict): Dictionary of code relationships
            max_distance (int): Maximum distance in the relationship graph
            
        Returns:
            dict: Dictionary of related codes by distance
        """
        if code not in relationships:
            print(f"Code {code} not found in the analyzed relationships")
            return {}
            
        # Track related codes by distance
        related_by_distance = defaultdict(set)
        visited = {code}
        
        # Add direct relationships (distance 1)
        for related_code in relationships.get(code, []):
            related_by_distance[1].add(related_code)
            visited.add(related_code)
        
        # Find extended relationships up to max_distance
        if max_distance > 1:
            current_level = set(relationships.get(code, []))
            
            for distance in range(2, max_distance + 1):
                next_level = set()
                
                for rel_code in current_level:
                    if rel_code in relationships:
                        for transitive_rel_code in relationships[rel_code]:
                            if transitive_rel_code not in visited:
                                related_by_distance[distance].add(transitive_rel_code)
                                visited.add(transitive_rel_code)
                                next_level.add(transitive_rel_code)
                
                if not next_level:
                    break
                    
                current_level = next_level
        
        return related_by_distance
    
    def generate_relationship_report(self, code, relationships, max_distance=2, output_file=None):
        """
        Generate a detailed report of code relationships.
        
        Args:
            code (str): The code to analyze
            relationships (dict): Dictionary of code relationships
            max_distance (int): Maximum relationship distance
            output_file (str, optional): Output file path
            
        Returns:
            str: Path to the created report
        """
        # Ensure we have data for this code
        details = self.fetch_code_details(code)
        if not details:
            print(f"Could not fetch details for code {code}")
            return None
        
        # Find related codes
        related_codes = self.find_related_diagnoses(code, relationships, max_distance)
        
        # Create report content
        content = {
            "code": code,
            "name": details.get("nameNorwegian", ""),
            "analyzed_at": datetime.now().isoformat(),
            "related_diagnoses": {}
        }
        
        # Add detailed information about the central code
        content["details"] = {
            "description": details.get("nameNorwegian", ""),
            "includes": details.get("includes", ""),
            "excludes": details.get("excludes", ""),
            "parent": details.get("parent", ""),
            "status": details.get("codeStatus", "")
        }
        
        # Add related diagnoses by distance
        for distance, codes in related_codes.items():
            content["related_diagnoses"][f"distance_{distance}"] = [
                {
                    "code": related_code,
                    "name": self.code_descriptions.get(related_code, "Unknown"),
                    "relationship_type": self._determine_relationship_type(code, related_code)
                }
                for related_code in codes
            ]
        
        # Create a pandas DataFrame for better reporting
        rows = []
        
        # Add the main code
        rows.append({
            "code": code,
            "name": details.get("nameNorwegian", ""),
            "distance": 0,
            "relationship_type": "self"
        })
        
        # Add related codes
        for distance, codes in related_codes.items():
            for related_code in codes:
                related_name = self.code_descriptions.get(related_code, "Unknown")
                relationship = self._determine_relationship_type(code, related_code)
                
                rows.append({
                    "code": related_code,
                    "name": related_name,
                    "distance": distance,
                    "relationship_type": relationship
                })
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        # Sort by distance, then code
        df = df.sort_values(["distance", "code"])
        
        # Create output file path if not provided
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(OUTPUT_DIR, f"{code}_relationships_{timestamp}.xlsx")
        
        # Save to Excel
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Main table
            df.to_excel(writer, sheet_name="Relationships", index=False)
            
            # Code details
            pd.DataFrame([{
                "Property": key,
                "Value": value
            } for key, value in content["details"].items()]).to_excel(
                writer, sheet_name="Code Details", index=False)
        
        print(f"Generated relationship report at {output_file}")
        
        # Also save as JSON for programmatic access
        json_file = output_file.replace('.xlsx', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        
        print(f"Generated JSON report at {json_file}")
        
        return output_file
    
    def _determine_relationship_type(self, source_code, target_code):
        """
        Determine the type of relationship between two codes.
        
        Args:
            source_code (str): Source code
            target_code (str): Target code
            
        Returns:
            str: Relationship type
        """
        # Check code patterns
        source_prefix = source_code.split('.')[0] if '.' in source_code else source_code
        target_prefix = target_code.split('.')[0] if '.' in target_code else target_code
        
        if source_prefix == target_prefix:
            return "same_category"
            
        # Check for specific chapter relationships (e.g., F codes, Z codes)
        source_chapter = source_code[0] if source_code else ''
        target_chapter = target_code[0] if target_code else ''
        
        if source_chapter == target_chapter:
            return "same_chapter"
            
        return "other"
    
    def visualize_relationships(self, code, relationships, max_distance=2, output_file=None):
        """
        Visualize the relationships for a specific code.
        
        Args:
            code (str): The code to visualize relationships for
            relationships (dict): Dictionary of code relationships
            max_distance (int): Maximum relationship distance
            output_file (str, optional): Output file path
            
        Returns:
            str: Path to the created visualization
        """
        # Find related codes
        related_codes = self.find_related_diagnoses(code, relationships, max_distance)
        
        # Flatten the related codes by distance
        all_related = {code}  # Start with the central code
        for distance, codes in related_codes.items():
            all_related.update(codes)
        
        # Create a graph to represent the relationships
        import networkx as nx
        G = nx.DiGraph()
        
        # Add the central node
        G.add_node(code, type="central", name=self.code_descriptions.get(code, ""))
        
        # Add related nodes
        for distance, codes in related_codes.items():
            for related_code in codes:
                G.add_node(related_code, 
                           type="related", 
                           distance=distance,
                           name=self.code_descriptions.get(related_code, ""))
        
        # Add edges based on direct relationships
        for node in all_related:
            if node in relationships:
                for related in relationships[node]:
                    if related in all_related:
                        G.add_edge(node, related)
        
        # Create visualization
        plt.figure(figsize=(20, 15))
        
        # Set up layout - spring layout often works well for relationship graphs
        pos = nx.spring_layout(G, k=0.5, iterations=100, seed=42)
        
        # Prepare node colors based on type and distance
        node_colors = []
        for node in G.nodes():
            if node == code:
                # Central node
                node_colors.append('red')
            elif G.nodes[node].get('distance', 0) == 1:
                # Direct relationships
                node_colors.append('lightblue')
            else:
                # Indirect relationships
                node_colors.append('lightgray')
        
        # Draw nodes
        nx.draw_networkx_nodes(
            G, pos, 
            node_size=700, 
            node_color=node_colors, 
            alpha=0.8
        )
        
        # Draw edges
        nx.draw_networkx_edges(
            G, pos,
            width=1.5,
            alpha=0.7,
            edge_color='gray',
            arrowsize=15
        )
        
        # Draw labels with code and brief description
        labels = {}
        for node in G.nodes():
            name = G.nodes[node].get('name', '')
            if name and len(name) > 20:
                name = name[:17] + "..."
            labels[node] = f"{node}\n{name}"
        
        nx.draw_networkx_labels(
            G, pos,
            labels=labels,
            font_size=9,
            font_weight='bold'
        )
        
        plt.title(f"Relationships for {code}: {self.code_descriptions.get(code, '')}")
        plt.axis('off')
        
        # Save the visualization
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(OUTPUT_DIR, f"{code}_relationships_{timestamp}.png")
        
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Saved relationship visualization to {output_file}")
        return output_file

def fetch_complete_f_codes():
    """
    Fetch a comprehensive set of F codes (mental disorders).
    
    Returns:
        list: List of F code dictionaries
    """
    print("Fetching mental disorder (F) codes...")
    url = f"{BASE_API_URL}/V/hierarchy"
    
    try:
        response = requests.get(url, headers=API_HEADERS)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract F codes recursively
            f_codes = []
            
            def extract_f_codes(node):
                if isinstance(node, dict) and 'codeValue' in node:
                    code_value = node.get('codeValue')
                    if isinstance(code_value, str) and code_value.startswith('F') and len(code_value) > 1:
                        f_codes.append(node)
                
                if isinstance(node, dict) and 'children' in node and node['children']:
                    for child in node['children']:
                        extract_f_codes(child)
            
            # Start extraction from the root
            extract_f_codes(data)
            
            print(f"Found {len(f_codes)} F codes")
            return f_codes
        else:
            print(f"Error {response.status_code} fetching F codes")
            return []
    except Exception as e:
        print(f"Error fetching F codes: {e}")
        return []

def analyze_f_code_clusters():
    """
    Analyze F code clusters and their relationships.
    
    Returns:
        tuple: (analyzer, relationships)
    """
    # Fetch all F codes
    f_codes = fetch_complete_f_codes()
    
    if not f_codes:
        print("No F codes found")
        return None, None
    
    # Extract code values
    code_values = [code['codeValue'] for code in f_codes]
    
    # Create analyzer
    analyzer = DiagnosticAnalyzer()
    
    # Analyze relationships
    relationships = analyzer.analyze_code_relationships(code_values)
    
    # For each main category (F0, F1, etc.), analyze relationships
    categories = {}
    for code in code_values:
        if len(code) >= 2:
            prefix = code[:2]
            if prefix in categories:
                categories[prefix].append(code)
            else:
                categories[prefix] = [code]
    
    # Generate reports for each major category
    for category, codes in categories.items():
        if len(codes) > 0:
            representative = codes[0]
            print(f"Analyzing category {category} using {representative} as representative")
            
            # Generate report
            analyzer.generate_relationship_report(
                representative, 
                relationships,
                output_file=os.path.join(OUTPUT_DIR, f"{category}_analysis.xlsx")
            )
            
            # Visualize relationships
            analyzer.visualize_relationships(
                representative,
                relationships,
                output_file=os.path.join(OUTPUT_DIR, f"{category}_relationships.png")
            )
    
    return analyzer, relationships

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze relationships between diagnostic codes.')
    
    parser.add_argument('--code', '-c', type=str,
                        help='Specific code to analyze')
    
    parser.add_argument('--related', '-r', action='store_true',
                        help='Find and analyze related codes')
    
    parser.add_argument('--distance', '-d', type=int, default=2,
                        help='Maximum relationship distance')
    
    parser.add_argument('--analyze-f', '-f', action='store_true',
                        help='Analyze all F codes (mental disorders)')
    
    parser.add_argument('--search', '-s', type=str,
                        help='Search for specific codes')
    
    parser.add_argument('--output-dir', '-o', type=str, default=OUTPUT_DIR,
                        help=f'Output directory (default: {OUTPUT_DIR})')
    
    return parser.parse_args()

def main():
    """Main function."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Update output directory
    global OUTPUT_DIR
    OUTPUT_DIR = args.output_dir
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Create analyzer
    analyzer = DiagnosticAnalyzer()
    
    # Handle search
    if args.search:
        print(f"Searching for: {args.search}")
        results = analyzer.search_codes(args.search)
        
        if results:
            print(f"Found {len(results)} results:")
            df = pd.DataFrame([{
                "code": result.get("code_value", ""),
                "name": result.get("name_norwegian", ""),
                "type": result.get("oid_system", "")
            } for result in results])
            
            # Save results to Excel
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            search_file = os.path.join(OUTPUT_DIR, f"search_{args.search.replace(' ', '_')}_{timestamp}.xlsx")
            df.to_excel(search_file, index=False)
            print(f"Saved search results to {search_file}")
            
            # Print top results
            for _, row in df.head(10).iterrows():
                print(f"{row['code']}: {row['name']}")
        else:
            print("No results found")
    
    # Handle specific code analysis
    elif args.code:
        print(f"Analyzing code: {args.code}")
        
        # Fetch code details
        details = analyzer.fetch_code_details(args.code)
        
        if not details:
            print(f"Could not fetch details for {args.code}")
            return
        
        print(f"Code: {args.code} - {details.get('nameNorwegian', '')}")
        
        # Analyze related codes if requested
        if args.related:
            # Find directly related codes
            print(f"Finding codes related to {args.code} (distance <= {args.distance})...")
            
            # Start with the main code
            codes_to_analyze = [args.code]
            
            # Analyze relationships
            relationships = analyzer.analyze_code_relationships(codes_to_analyze)
            
            # Find related codes
            related_codes = analyzer.find_related_diagnoses(args.code, relationships, args.distance)
            
            # Flatten the related codes
            all_related = set()
            for distance, codes in related_codes.items():
                print(f"Found {len(codes)} codes at distance {distance}")
                all_related.update(codes)
            
            # Analyze the expanded set of codes
            if all_related:
                print(f"Analyzing relationships among all {len(all_related)} related codes...")
                relationships.update(analyzer.analyze_code_relationships(all_related))
            
            # Generate report
            analyzer.generate_relationship_report(args.code, relationships, args.distance)
            
            # Visualize relationships
            analyzer.visualize_relationships(args.code, relationships, args.distance)
    
    # Analyze all F codes
    elif args.analyze_f:
        print("Analyzing all F codes (mental disorders)")
        analyze_f_code_clusters()
    
    else:
        print("No action specified. Use -h for help.")
        parser.print_help()

if __name__ == "__main__":
    main()
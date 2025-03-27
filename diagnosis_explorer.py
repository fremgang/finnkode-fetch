#!/usr/bin/env python
"""
Comprehensive Diagnosis Explorer

A complete tool for fetching, analyzing, and visualizing diagnostic codes
from the Finnkode API, with special support for ICD-10 mental disorder codes.

This script combines the functionality of various modules to provide an
end-to-end solution for exploring diagnostic hierarchies and relationships.
"""
import os
import sys
import json
import argparse
import pandas as pd
from datetime import datetime
import subprocess
import matplotlib.pyplot as plt
from pathlib import Path

# Add the project root to the path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

# Define directories
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
ANALYSIS_DIR = os.path.join(PROJECT_ROOT, "analysis_output")
VISUALIZATIONS_DIR = os.path.join(PROJECT_ROOT, "visualizations")

# Create directories if they don't exist
for directory in [OUTPUT_DIR, ANALYSIS_DIR, VISUALIZATIONS_DIR]:
    os.makedirs(directory, exist_ok=True)

def run_fetch_hierarchy(args):
    """
    Run the hierarchical fetcher with the given arguments.
    
    Args:
        args (argparse.Namespace): Command line arguments
    
    Returns:
        str: Path to the output file
    """
    print("\n===== FETCHING DIAGNOSTIC HIERARCHY =====")
    
    # Construct command
    cmd = [
        sys.executable,
        os.path.join(PROJECT_ROOT, "hierarchical_fetcher.py"),
        "--code", args.code,
        "--depth", str(args.depth),
        "--batch", str(args.batch),
        "--output-dir", OUTPUT_DIR,
        "--viz-dir", VISUALIZATIONS_DIR
    ]
    
    if args.no_visualize:
        cmd.append("--no-visualize")
    
    # Run the command
    print(f"Running: {' '.join(cmd)}")
    process = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print output
    print(process.stdout)
    if process.stderr:
        print("ERRORS:")
        print(process.stderr)
    
    # Find the latest hierarchy file
    hierarchy_files = sorted(
        [f for f in os.listdir(OUTPUT_DIR) if f.startswith("complete_hierarchy_") and f.endswith(".json")],
        reverse=True
    )
    
    if hierarchy_files:
        return os.path.join(OUTPUT_DIR, hierarchy_files[0])
    return None

def run_create_visualization(hierarchy_file, args):
    """
    Create an interactive visualization from a hierarchy file.
    
    Args:
        hierarchy_file (str): Path to the hierarchy file
        args (argparse.Namespace): Command line arguments
    
    Returns:
        str: Path to the output HTML file
    """
    print("\n===== CREATING INTERACTIVE VISUALIZATION =====")
    
    # Construct command
    cmd = [
        sys.executable,
        os.path.join(PROJECT_ROOT, "interactive_viz.py"),
        "--input", hierarchy_file,
        "--output", os.path.join(VISUALIZATIONS_DIR, f"interactive_{args.code}_hierarchy.html"),
        "--title", f"ICD-10 {args.code} Diagnostic Hierarchy"
    ]
    
    # Run the command
    print(f"Running: {' '.join(cmd)}")
    process = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print output
    print(process.stdout)
    if process.stderr:
        print("ERRORS:")
        print(process.stderr)
    
    output_file = os.path.join(VISUALIZATIONS_DIR, f"interactive_{args.code}_hierarchy.html")
    if os.path.exists(output_file):
        return output_file
    return None

def run_analyze_relationships(args):
    """
    Run the diagnostic analyzer to analyze code relationships.
    
    Args:
        args (argparse.Namespace): Command line arguments
    
    Returns:
        str: Path to the relationship report
    """
    print("\n===== ANALYZING CODE RELATIONSHIPS =====")
    
    # Determine the code to analyze
    code = args.analyze_code or args.code
    
    # Construct command
    cmd = [
        sys.executable,
        os.path.join(PROJECT_ROOT, "diagnostic_analyzer.py"),
        "--code", code,
        "--related",
        "--distance", str(args.relationship_distance),
        "--output-dir", ANALYSIS_DIR
    ]
    
    # Run the command
    print(f"Running: {' '.join(cmd)}")
    process = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print output
    print(process.stdout)
    if process.stderr:
        print("ERRORS:")
        print(process.stderr)
    
    # Find the latest relationship report
    report_files = sorted(
        [f for f in os.listdir(ANALYSIS_DIR) if f.startswith(f"{code}_relationships_") and f.endswith(".xlsx")],
        reverse=True
    )
    
    if report_files:
        return os.path.join(ANALYSIS_DIR, report_files[0])
    return None

def run_search_codes(query):
    """
    Run a search for diagnostic codes.
    
    Args:
        query (str): Search query
    
    Returns:
        str: Path to the search results file
    """
    print(f"\n===== SEARCHING FOR: {query} =====")
    
    # Construct command
    cmd = [
        sys.executable,
        os.path.join(PROJECT_ROOT, "diagnostic_analyzer.py"),
        "--search", query,
        "--output-dir", ANALYSIS_DIR
    ]
    
    # Run the command
    print(f"Running: {' '.join(cmd)}")
    process = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print output
    print(process.stdout)
    if process.stderr:
        print("ERRORS:")
        print(process.stderr)
    
    # Find the latest search results file
    search_files = sorted(
        [f for f in os.listdir(ANALYSIS_DIR) if f.startswith(f"search_{query.replace(' ', '_')}_") and f.endswith(".xlsx")],
        reverse=True
    )
    
    if search_files:
        return os.path.join(ANALYSIS_DIR, search_files[0])
    return None

def analyze_f_code_categories():
    """
    Run an analysis of all F-code categories.
    
    Returns:
        str: Path to the output directory
    """
    print("\n===== ANALYZING F-CODE CATEGORIES =====")
    
    # Construct command
    cmd = [
        sys.executable,
        os.path.join(PROJECT_ROOT, "diagnostic_analyzer.py"),
        "--analyze-f",
        "--output-dir", ANALYSIS_DIR
    ]
    
    # Run the command
    print(f"Running: {' '.join(cmd)}")
    process = subprocess.run(cmd, capture_output=True, text=True)
    
    # Print output
    print(process.stdout)
    if process.stderr:
        print("ERRORS:")
        print(process.stderr)
    
    return ANALYSIS_DIR

def generate_summary_report(args, files):
    """
    Generate a summary report of all executed operations.
    
    Args:
        args (argparse.Namespace): Command line arguments
        files (dict): Dictionary of output files from various operations
    
    Returns:
        str: Path to the summary report
    """
    print("\n===== GENERATING SUMMARY REPORT =====")
    
    # Create a summary DataFrame
    operations = []
    
    for operation, file_path in files.items():
        if file_path:
            operations.append({
                "Operation": operation,
                "Output File": file_path,
                "File Size": f"{os.path.getsize(file_path) / 1024:.1f} KB",
                "Created": datetime.fromtimestamp(os.path.getctime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
            })
    
    operations_df = pd.DataFrame(operations)
    
    # Create a summary of parameters
    params = [
        {"Parameter": "Code", "Value": args.code},
        {"Parameter": "Depth", "Value": args.depth},
        {"Parameter": "Batch Size", "Value": args.batch},
        {"Parameter": "Relationship Distance", "Value": args.relationship_distance},
        {"Parameter": "Search Query", "Value": args.search},
        {"Parameter": "Analyze F-Codes", "Value": args.analyze_f_codes},
        {"Parameter": "Output Directory", "Value": OUTPUT_DIR},
        {"Parameter": "Analysis Directory", "Value": ANALYSIS_DIR},
        {"Parameter": "Visualizations Directory", "Value": VISUALIZATIONS_DIR}
    ]
    
    params_df = pd.DataFrame(params)
    
    # Generate Excel report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(OUTPUT_DIR, f"summary_report_{timestamp}.xlsx")
    
    with pd.ExcelWriter(report_file, engine="openpyxl") as writer:
        operations_df.to_excel(writer, sheet_name="Operations", index=False)
        params_df.to_excel(writer, sheet_name="Parameters", index=False)
        
        # Add a summary sheet
        summary_data = [
            {"Metric": "Date", "Value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"Metric": "Total Operations", "Value": len(operations)},
            {"Metric": "Main Code", "Value": args.code},
            {"Metric": "Search Query", "Value": args.search or "N/A"}
        ]
        
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)
    
    print(f"Generated summary report at {report_file}")
    return report_file

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Diagnosis Explorer: Fetch, analyze, and visualize diagnostic codes"
    )
    
    parser.add_argument(
        "--code", "-c", 
        type=str, 
        default="V",
        help="Starting code for hierarchy fetching (default: V for mental disorders)"
    )
    
    parser.add_argument(
        "--depth", "-d", 
        type=int, 
        default=5,
        help="Maximum depth to fetch in the hierarchy (default: 5)"
    )
    
    parser.add_argument(
        "--batch", "-b", 
        type=int, 
        default=10,
        help="Batch size for concurrent API requests (default: 10)"
    )
    
    parser.add_argument(
        "--analyze-code", "-a", 
        type=str,
        help="Specific code to analyze relationships for (default: same as --code)"
    )
    
    parser.add_argument(
        "--relationship-distance", "-r", 
        type=int, 
        default=2,
        help="Maximum relationship distance (default: 2)"
    )
    
    parser.add_argument(
        "--search", "-s", 
        type=str,
        help="Search for specific diagnostic codes"
    )
    
    parser.add_argument(
        "--analyze-f-codes", "-f", 
        action="store_true",
        help="Analyze all F codes (mental disorders)"
    )
    
    parser.add_argument(
        "--no-visualize", 
        action="store_true",
        help="Skip creating visualizations"
    )
    
    parser.add_argument(
        "--fetch-only", 
        action="store_true",
        help="Only fetch hierarchy data without analysis"
    )
    
    parser.add_argument(
        "--analyze-only", 
        action="store_true",
        help="Only analyze existing data without fetching"
    )
    
    return parser.parse_args()

def main():
    """Main function."""
    print("===== COMPREHENSIVE DIAGNOSIS EXPLORER =====")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Track output files
    output_files = {}
    
    # Handle search
    if args.search:
        search_results = run_search_codes(args.search)
        if search_results:
            output_files["Search Results"] = search_results
        return
    
    # Skip fetching if analyze-only is specified
    hierarchy_file = None
    if not args.analyze_only:
        # Fetch hierarchy
        hierarchy_file = run_fetch_hierarchy(args)
        if hierarchy_file:
            output_files["Hierarchy Data"] = hierarchy_file
        
        # Create interactive visualization
        if hierarchy_file and not args.no_visualize:
            viz_file = run_create_visualization(hierarchy_file, args)
            if viz_file:
                output_files["Interactive Visualization"] = viz_file
    
    # Skip analysis if fetch-only is specified
    if not args.fetch_only:
        # Analyze relationships
        if args.analyze_code or args.code != "V":
            relationship_report = run_analyze_relationships(args)
            if relationship_report:
                output_files["Relationship Analysis"] = relationship_report
        
        # Analyze F-code categories
        if args.analyze_f_codes:
            f_analysis_dir = analyze_f_code_categories()
            if f_analysis_dir:
                output_files["F-Code Analysis"] = f_analysis_dir
    
    # Generate summary report
    summary_report = generate_summary_report(args, output_files)
    if summary_report:
        output_files["Summary Report"] = summary_report
    
    print("\n===== EXECUTION COMPLETE =====")
    print("Output files:")
    for operation, file_path in output_files.items():
        print(f"- {operation}: {file_path}")

if __name__ == "__main__":
    main()
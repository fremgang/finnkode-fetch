# Enhanced Diagnostic Code Explorer

An advanced tool suite for fetching, analyzing, and visualizing ICD-10 diagnostic codes from the Finnkode API, with special support for mental disorder codes (F00-F99).

## Overview

This enhanced version of the Finnkode Fetcher provides comprehensive capabilities for exploring the hierarchical structure of diagnostic codes, analyzing relationships between diagnoses, and creating interactive visualizations for better understanding of medical coding systems.

## Features

- **Complete Hierarchical Fetching**: Recursively fetch all levels of the diagnostic hierarchy, including subdiagnoses and specific codes
- **Relationship Analysis**: Discover and analyze relationships between diagnostic codes
- **Interactive Visualizations**: Create interactive web-based visualizations of diagnostic hierarchies
- **Advanced Network Analysis**: View connections between related diagnoses with network graphs
- **Comprehensive Reporting**: Generate detailed reports on diagnostic code relationships

## Project Structure

```
diagnostic-explorer/
├── README.md
├── requirements.txt
├── hierarchical_fetcher.py   # Enhanced fetcher for complete hierarchical data
├── interactive_viz.py        # Creates interactive web visualizations
├── diagnostic_analyzer.py    # Analyzes relationships between diagnoses
├── diagnosis_explorer.py     # Comprehensive wrapper for all functionality
├── output/                   # Directory for raw data output
├── analysis_output/          # Directory for analysis results
└── visualizations/           # Directory for visualization files
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/diagnostic-explorer.git
   cd diagnostic-explorer
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Quick Start

To run a complete pipeline that fetches, analyzes, and visualizes mental disorder codes:

```bash
python diagnosis_explorer.py --code V --analyze-f-codes
```

This will:
1. Fetch the complete hierarchy of mental disorder codes
2. Create visualizations of the hierarchy
3. Analyze relationships between F-codes
4. Generate a summary report

## Usage Guide

### Fetching Complete Diagnostic Hierarchies

The `hierarchical_fetcher.py` script can fetch complete hierarchical data for diagnostic codes:

```bash
python hierarchical_fetcher.py --code V --depth 5
```

Options:
- `--code, -c`: Starting code for hierarchy fetching (default: V for mental disorders)
- `--depth, -d`: Maximum depth to fetch in the hierarchy (default: 5)
- `--batch, -b`: Batch size for concurrent API requests (default: 10)
- `--specific-code, -s`: Fetch information for a specific code only
- `--visualize-only`: Only create visualizations from existing data
- `--no-visualize`: Skip visualization creation

Example: Fetch a specific diagnostic code with details:

```bash
python hierarchical_fetcher.py --specific-code F32.1
```

### Creating Interactive Visualizations

The `interactive_viz.py` script creates interactive web-based visualizations of diagnostic hierarchies:

```bash
python interactive_viz.py --input output/complete_hierarchy_20250327_120000.json --title "Mental Disorders Hierarchy"
```

Options:
- `--input, -i`: Input JSON file containing hierarchy data (required)
- `--output, -o`: Output HTML file path
- `--title, -t`: Title for the visualization

The interactive visualization allows you to:
- Click on diagnoses to zoom into subcategories
- Navigate through the hierarchy using breadcrumbs
- Search for specific diagnostic codes
- View detailed information about each diagnosis

### Analyzing Diagnostic Relationships

The `diagnostic_analyzer.py` script analyzes relationships between diagnostic codes:

```bash
python diagnostic_analyzer.py --code F32 --related --distance 2
```

Options:
- `--code, -c`: Specific code to analyze
- `--related, -r`: Find and analyze related codes
- `--distance, -d`: Maximum relationship distance (default: 2)
- `--analyze-f, -f`: Analyze all F codes (mental disorders)
- `--search, -s`: Search for specific codes

Example: Search for diagnostic codes related to depression:

```bash
python diagnostic_analyzer.py --search "depression"
```

### Comprehensive Explorer

The `diagnosis_explorer.py` script provides a comprehensive wrapper for all functionality:

```bash
python diagnosis_explorer.py --code F3 --depth 4 --relationship-distance 3
```

Options:
- `--code, -c`: Starting code for hierarchy fetching (default: V for mental disorders)
- `--depth, -d`: Maximum depth to fetch in the hierarchy (default: 5)
- `--batch, -b`: Batch size for concurrent API requests (default: 10)
- `--analyze-code, -a`: Specific code to analyze relationships for
- `--relationship-distance, -r`: Maximum relationship distance (default: 2)
- `--search, -s`: Search for specific diagnostic codes
- `--analyze-f-codes, -f`: Analyze all F codes (mental disorders)
- `--no-visualize`: Skip creating visualizations
- `--fetch-only`: Only fetch hierarchy data without analysis
- `--analyze-only`: Only analyze existing data without fetching

## Examples

### Example 1: Complete Analysis of Depressive Disorders

```bash
python diagnosis_explorer.py --code F32 --depth 4 --relationship-distance 2
```

This will:
1. Fetch the complete hierarchy of depressive disorders (F32)
2. Create visualizations of the hierarchy
3. Analyze relationships between F32 and related codes
4. Generate a summary report

### Example 2: Search and Analyze Specific Condition

```bash
# First search for the condition
python diagnosis_explorer.py --search "bipolar disorder"

# Then analyze the specific code using the results from the search
python diagnosis_explorer.py --analyze-code F31 --relationship-distance 3
```

### Example 3: Comprehensive Analysis of Mental Disorders

```bash
python diagnosis_explorer.py --code V --depth 6 --analyze-f-codes
```

This will:
1. Fetch the complete hierarchy of all mental disorders
2. Analyze all F-code categories and their relationships
3. Create comprehensive visualizations
4. Generate detailed reports

## Understanding the Output

The tool generates several types of output:

### Hierarchical Data

JSON files in the `output/` directory contain the complete hierarchical structure of diagnostic codes. Each node includes:
- `codeValue`: The ICD-10 code 
- `nameNorwegian`: The diagnosis name
- `children`: Array of child diagnoses
- Additional metadata like status, inclusion/exclusion criteria, etc.

### Visualizations

- **Network graphs**: PNG files in the `visualizations/` directory showing relationships between diagnoses
- **Interactive sunburst charts**: HTML files providing interactive exploration of the hierarchy
- **Treemaps**: Visualizations showing the relative size of diagnostic categories

### Analysis Reports

Excel files in the `analysis_output/` directory containing:
- Relationship tables showing connections between diagnoses
- Detailed information about each code
- Statistics on diagnosis categories and subcategories

## Advanced Usage

### Custom Data Extraction

You can use the code as a library to extract custom data:

```python
from hierarchical_fetcher import build_complete_hierarchy, extract_all_codes

# Fetch the hierarchy
hierarchy = build_complete_hierarchy(parent_code="F30", max_depth=3)

# Extract all codes as a flat list
codes = extract_all_codes(hierarchy)

# Process the codes
for code in codes:
    print(f"{code['codeValue']}: {code['nameNorwegian']}")
```

### Customizing Visualizations

You can modify the visualization templates in `interactive_viz.py` to create custom visualizations.

## Requirements

- Python 3.7+
- Required packages:
  - requests
  - pandas
  - matplotlib
  - seaborn
  - networkx
  - tqdm
  - openpyxl

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
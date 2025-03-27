#!/usr/bin/env python
"""
Interactive visualization tool for displaying diagnostic code hierarchies.
This tool creates an HTML file with an interactive sunburst chart.
"""
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

def convert_hierarchy_for_viz(hierarchy_data):
    """
    Convert the hierarchy data into a format suitable for D3.js visualization.
    
    Args:
        hierarchy_data (dict): Raw hierarchy data from the API
        
    Returns:
        dict: Converted data for visualization
    """
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
    
    return process_node(hierarchy_data)

def generate_html_template(data_json, title="Diagnostic Code Hierarchy"):
    """
    Generate an HTML template with embedded D3.js for visualization.
    
    Args:
        data_json (str): JSON data as a string
        title (str): Title for the visualization
        
    Returns:
        str: Complete HTML document
    """
    html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f9f9f9;
            overflow-x: hidden;
        }}
        #container {{
            display: flex;
            flex-direction: column;
            max-width: 1200px;
            margin: 0 auto;
        }}
        #visualization {{
            margin-top: 20px;
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        #controls {{
            margin-bottom: 20px;
            padding: 10px 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        #infoPanel {{
            margin-top: 20px;
            min-height: 100px;
            padding: 15px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .breadcrumbs {{
            margin-bottom: 15px;
            padding: 10px 0;
            font-size: 14px;
        }}
        .breadcrumb-item {{
            display: inline-block;
            padding: 4px 8px;
            margin-right: 5px;
            background-color: #f0f0f0;
            border-radius: 4px;
            cursor: pointer;
        }}
        .breadcrumb-item:hover {{
            background-color: #e0e0e0;
        }}
        .breadcrumb-divider {{
            margin: 0 5px;
            color: #999;
        }}
        h1 {{
            color: #333;
        }}
        .node {{
            cursor: pointer;
        }}
        .node:hover {{
            opacity: 0.8;
        }}
        .tooltip {{
            position: absolute;
            padding: 8px 12px;
            font: 12px sans-serif;
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid #ddd;
            border-radius: 4px;
            pointer-events: none;
            z-index: 10;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
        }}
        .code-details {{
            margin-top: 10px;
        }}
        .code-title {{
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .code-value {{
            font-family: monospace;
            background-color: #f0f0f0;
            padding: 2px 5px;
            border-radius: 3px;
        }}
        .code-description {{
            margin-top: 10px;
        }}
        .search-container {{
            margin-bottom: 15px;
        }}
        #searchInput {{
            padding: 8px 12px;
            width: 250px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }}
        #searchButton {{
            padding: 8px 16px;
            background-color: #4285f4;
            border: none;
            border-radius: 4px;
            color: white;
            cursor: pointer;
            margin-left: 10px;
        }}
        #searchButton:hover {{
            background-color: #3367d6;
        }}
        .search-results {{
            margin-top: 10px;
            max-height: 200px;
            overflow-y: auto;
            border: 1px solid #eee;
            border-radius: 4px;
            padding: 5px;
            display: none;
        }}
        .search-result-item {{
            padding: 5px 10px;
            cursor: pointer;
            border-bottom: 1px solid #f0f0f0;
        }}
        .search-result-item:hover {{
            background-color: #f5f5f5;
        }}
        .no-results {{
            padding: 10px;
            color: #666;
            font-style: italic;
        }}
        .legend {{
            display: flex;
            flex-wrap: wrap;
            margin-top: 15px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin-right: 20px;
            margin-bottom: 10px;
        }}
        .legend-color {{
            width: 15px;
            height: 15px;
            border-radius: 3px;
            margin-right: 5px;
        }}
    </style>
</head>
<body>
    <div id="container">
        <h1>{title}</h1>
        
        <div id="controls">
            <div class="search-container">
                <input type="text" id="searchInput" placeholder="Search for a diagnosis code...">
                <button id="searchButton">Search</button>
                <div id="searchResults" class="search-results"></div>
            </div>
            
            <div class="breadcrumbs" id="breadcrumbs">
                <span class="breadcrumb-item" data-id="root">Root</span>
            </div>
        </div>
        
        <div id="visualization"></div>
        
        <div id="infoPanel">
            <h3>Code Information</h3>
            <p>Click on a section in the visualization to see details about that code.</p>
        </div>
    </div>

    <script>
    // Parse the data from the embedded JSON
    const data = {data_json};
    
    // Set up dimensions for the visualization
    const width = document.getElementById('visualization').offsetWidth;
    const height = 600;
    const radius = Math.min(width, height) / 2;
    
    // Create the SVG container
    const svg = d3.select("#visualization")
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", `translate(${{width / 2}}, ${{height / 2}})`);
    
    // Create tooltip
    const tooltip = d3.select("body")
        .append("div")
        .attr("class", "tooltip")
        .style("opacity", 0);
    
    // Create a color scale (adjust for different categories)
    const colorScale = d3.scaleOrdinal(d3.schemeCategory10);
    
    // Create the partition layout
    const partition = d3.partition()
        .size([2 * Math.PI, radius]);
    
    // Create the arc generator
    const arc = d3.arc()
        .startAngle(d => d.x0)
        .endAngle(d => d.x1)
        .innerRadius(d => d.y0)
        .outerRadius(d => d.y1);
    
    // Create the hierarchy from the data
    const root = d3.hierarchy(data)
        .sum(d => d.value);
    
    // Apply the partition layout to the hierarchy
    partition(root);
    
    // All nodes array for searching
    let allNodes = [];
    root.eachBefore(d => {{
        if (d.data.id) {{
            allNodes.push(d);
        }}
    }});
    
    // Draw the visualization
    function drawSunburst(rootNode) {{
        // Clear existing visualization
        svg.selectAll("*").remove();
        
        // Create the slices
        const slice = svg.selectAll("path")
            .data(rootNode.descendants().filter(d => d.depth))
            .enter()
            .append("path")
            .attr("d", arc)
            .attr("class", "node")
            .style("fill", d => {{
                // Use different color schemes based on the first character of the ID
                if (d.data.id && d.data.id.startsWith('F')) {{
                    // Mental disorders - use a blue spectrum
                    return d3.interpolateBlues(0.3 + 0.7 * (d.depth / 5));
                }} else {{
                    // Other codes
                    return colorScale(d.depth);
                }}
            }})
            .style("stroke", "#fff")
            .style("stroke-width", "1px")
            .style("opacity", 0.8);
        
        // Add interactivity
        slice.on("mouseover", function(event, d) {{
                // Highlight the slice
                d3.select(this)
                    .style("opacity", 1);
                
                // Update tooltip
                tooltip.transition()
                    .duration(200)
                    .style("opacity", 0.9);
                tooltip.html(`
                    <strong>${{d.data.id}}</strong><br>
                    ${{d.data.name}}<br>
                    Depth: ${{d.depth}}
                `)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            }})
            .on("mouseout", function() {{
                // Reset the slice
                d3.select(this)
                    .style("opacity", 0.8);
                
                // Hide tooltip
                tooltip.transition()
                    .duration(500)
                    .style("opacity", 0);
            }})
            .on("click", function(event, d) {{
                updateInfoPanel(d);
                updateBreadcrumbs(d);
                
                // Zoom in if the node has children
                if (d.children && d.children.length > 0) {{
                    zoomToNode(d);
                }}
            }});
        
        // Center text (optional)
        svg.append("text")
            .attr("text-anchor", "middle")
            .attr("dy", "0.35em")
            .text(rootNode.data.name || "Root");
    }}
    
    // Function to zoom to a specific node
    function zoomToNode(node) {{
        // Create a new hierarchy based on the current node
        const newRoot = d3.hierarchy(node.data)
            .sum(d => d.value);
        
        // Apply the partition layout
        partition(newRoot);
        
        // Redraw the sunburst
        drawSunburst(newRoot);
    }}
    
    // Function to update the info panel
    function updateInfoPanel(node) {{
        const infoPanel = document.getElementById("infoPanel");
        
        // Format the information
        let html = `
            <div class="code-details">
                <div class="code-title">Diagnostic Code:</div>
                <span class="code-value">${{node.data.id || "N/A"}}</span>
                
                <div class="code-description">
                    <strong>Name:</strong> ${{node.data.name || "N/A"}}<br>
                    <strong>Level:</strong> ${{node.depth}}<br>
                </div>
            </div>
        `;
        
        // Add additional information if available
        if (node.data.value) {{
            html += `<div><strong>Value:</strong> ${{node.data.value}}</div>`;
        }}
        
        // Add parent information
        if (node.parent && node.parent.data.id) {{
            html += `
                <div style="margin-top: 15px;">
                    <strong>Parent Code:</strong> ${{node.parent.data.id}}<br>
                    <strong>Parent Name:</strong> ${{node.parent.data.name || "N/A"}}
                </div>
            `;
        }}
        
        // Add children information
        if (node.children && node.children.length > 0) {{
            html += `
                <div style="margin-top: 15px;">
                    <strong>Sub-categories (${{node.children.length}}):</strong>
                    <ul style="max-height: 150px; overflow-y: auto;">
                        ${{node.children.map(child => 
                            `<li><span class="code-value">${{child.data.id}}</span> - ${{child.data.name}}</li>`
                        ).join('')}}
                    </ul>
                </div>
            `;
        }} else {{
            html += `<div style="margin-top: 15px;"><em>This is a leaf node with no sub-categories.</em></div>`;
        }}
        
        infoPanel.innerHTML = html;
    }}
    
    // Function to update breadcrumbs
    function updateBreadcrumbs(node) {{
        const breadcrumbs = document.getElementById("breadcrumbs");
        
        // Clear existing breadcrumbs
        breadcrumbs.innerHTML = "";
        
        // Build the path back to the root
        const path = [];
        let current = node;
        
        while (current) {{
            path.unshift(current);
            current = current.parent;
        }}
        
        // Create new breadcrumbs
        path.forEach((node, index) => {{
            // Create breadcrumb item
            const item = document.createElement("span");
            item.className = "breadcrumb-item";
            item.textContent = node.data.id || "Root";
            item.setAttribute("data-id", node.data.id || "root");
            
            // Add click handler
            item.addEventListener("click", () => {{
                zoomToNode(node);
                updateInfoPanel(node);
                updateBreadcrumbs(node);
            }});
            
            // Add to breadcrumbs
            breadcrumbs.appendChild(item);
            
            // Add divider (except for the last item)
            if (index < path.length - 1) {{
                const divider = document.createElement("span");
                divider.className = "breadcrumb-divider";
                divider.textContent = ">";
                breadcrumbs.appendChild(divider);
            }}
        }});
    }}
    
    // Search functionality
    document.getElementById("searchButton").addEventListener("click", performSearch);
    document.getElementById("searchInput").addEventListener("keyup", function(event) {{
        if (event.key === "Enter") {{
            performSearch();
        }}
    }});
    
    function performSearch() {{
        const searchTerm = document.getElementById("searchInput").value.trim().toLowerCase();
        const resultsContainer = document.getElementById("searchResults");
        
        if (!searchTerm) {{
            resultsContainer.style.display = "none";
            return;
        }}
        
        // Filter nodes based on the search term
        const results = allNodes.filter(node => {{
            const id = node.data.id ? node.data.id.toLowerCase() : "";
            const name = node.data.name ? node.data.name.toLowerCase() : "";
            
            return id.includes(searchTerm) || name.includes(searchTerm);
        }});
        
        // Display results
        resultsContainer.innerHTML = "";
        resultsContainer.style.display = "block";
        
        if (results.length === 0) {{
            resultsContainer.innerHTML = '<div class="no-results">No matching codes found</div>';
            return;
        }}
        
        // Sort results (codes with the search term at the beginning come first)
        results.sort((a, b) => {{
            const aId = a.data.id ? a.data.id.toLowerCase() : "";
            const bId = b.data.id ? b.data.id.toLowerCase() : "";
            
            // If one starts with the search term and the other doesn't
            if (aId.startsWith(searchTerm) && !bId.startsWith(searchTerm)) return -1;
            if (!aId.startsWith(searchTerm) && bId.startsWith(searchTerm)) return 1;
            
            // Otherwise sort alphabetically
            return aId.localeCompare(bId);
        }});
        
        // Limit to top 20 results
        const limitedResults = results.slice(0, 20);
        
        // Create result items
        limitedResults.forEach(node => {{
            const resultItem = document.createElement("div");
            resultItem.className = "search-result-item";
            resultItem.innerHTML = `<strong>${{node.data.id}}</strong> - ${{node.data.name}}`;
            
            resultItem.addEventListener("click", () => {{
                // Navigate to this node
                zoomToNode(findNodeInHierarchy(root, node.data.id));
                updateInfoPanel(node);
                updateBreadcrumbs(node);
                
                // Clear search
                resultsContainer.style.display = "none";
                document.getElementById("searchInput").value = "";
            }});
            
            resultsContainer.appendChild(resultItem);
        }});
    }}
    
    // Helper function to find a node by ID in the hierarchy
    function findNodeInHierarchy(root, id) {{
        let found = null;
        
        function search(node) {{
            if (node.data.id === id) {{
                found = node;
                return;
            }}
            
            if (node.children) {{
                for (const child of node.children) {{
                    search(child);
                    if (found) break;
                }}
            }}
        }}
        
        search(root);
        return found || root;
    }}
    
    // Initialize the visualization
    drawSunburst(root);
    </script>
</body>
</html>'''
    
    return html_template

def create_interactive_visualization(hierarchy_data, output_file=None, title="ICD-10 Diagnostic Code Hierarchy"):
    """
    Create an interactive HTML visualization from hierarchy data.
    
    Args:
        hierarchy_data (dict): Hierarchy data
        output_file (str, optional): Output file path
        title (str): Title for the visualization
        
    Returns:
        str: Path to the created HTML file
    """
    # Convert the hierarchy data for visualization
    viz_data = convert_hierarchy_for_viz(hierarchy_data)
    
    # Convert to JSON string for embedding in HTML
    data_json = json.dumps(viz_data)
    
    # Generate the HTML content
    html_content = generate_html_template(data_json, title)
    
    # Create output file path if not provided
    if not output_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join("visualizations", f"interactive_hierarchy_{timestamp}.html")
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write the HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Created interactive visualization at {output_file}")
    return output_file

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Create interactive diagnostic code hierarchy visualization.')
    
    parser.add_argument('--input', '-i', type=str, required=True,
                        help='Input JSON file containing hierarchy data')
    
    parser.add_argument('--output', '-o', type=str,
                        help='Output HTML file path')
    
    parser.add_argument('--title', '-t', type=str, default="ICD-10 Diagnostic Code Hierarchy",
                        help='Title for the visualization')
    
    return parser.parse_args()

def main():
    """Main function."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Check if input file exists
    if not os.path.isfile(args.input):
        print(f"Error: Input file '{args.input}' not found")
        return
    
    # Read the input JSON file
    print(f"Reading hierarchy data from {args.input}")
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            hierarchy_data = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: {args.input} is not a valid JSON file")
        return
    except Exception as e:
        print(f"Error reading {args.input}: {e}")
        return
    
    # Create the visualization
    output_file = args.output or os.path.join(
        "visualizations", 
        f"interactive_{Path(args.input).stem}.html"
    )
    
    create_interactive_visualization(hierarchy_data, output_file, args.title)

if __name__ == "__main__":
    main()
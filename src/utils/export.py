"""
Utilities for exporting data to various formats.
"""
import pandas as pd
import os

def create_dataframe_from_results(results):
    """
    Convert API results to a pandas DataFrame for easier analysis.
    
    Args:
        results (list): Results from the API
        
    Returns:
        pandas.DataFrame: DataFrame containing the results
    """
    if not results:
        return pd.DataFrame()
        
    # Extract all possible fields from the results
    all_fields = set()
    for item in results:
        all_fields.update(item.keys())
    
    # Create rows for the DataFrame
    rows = []
    for item in results:
        row = {field: item.get(field, None) for field in all_fields}
        rows.append(row)
        
    return pd.DataFrame(rows)
    
def create_dataframe_from_mental_disorders(codes):
    """
    Convert mental disorder codes to a pandas DataFrame.
    
    Args:
        codes (list): List of mental disorder code dictionaries
        
    Returns:
        pandas.DataFrame: DataFrame containing the codes
    """
    if not codes:
        return pd.DataFrame()
    
    # Extract relevant fields
    columns = [
        'codeValue', 'nameNorwegian', 'active', 'isLeafNode', 
        'sortIndex', 'activeOnlySortIndex'
    ]
    
    rows = []
    for code in codes:
        row = {col: code.get(col, None) for col in columns}
        
        # Add the path as a string
        if 'path' in code:
            row['path'] = ' > '.join(code['path'])
            
        rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Ensure the code is the first column
    if 'codeValue' in df.columns:
        cols = ['codeValue'] + [col for col in df.columns if col != 'codeValue']
        df = df[cols]
    
    return df

def export_to_csv(df, filename, output_dir="output"):
    """
    Export a DataFrame to CSV file.
    
    Args:
        df (pandas.DataFrame): DataFrame to export
        filename (str): Output filename
        output_dir (str): Directory to save the output file
    
    Returns:
        str: Path to the created file
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Full path for the output file
    filepath = os.path.join(output_dir, filename)
    
    # Export to CSV
    df.to_csv(filepath, index=False, encoding='utf-8')
    print(f"Exported {len(df)} rows to {filepath}")
    
    return filepath

def export_to_excel(results_dict, filename, output_dir="output"):
    """
    Export multiple DataFrames to an Excel file with multiple sheets.
    
    Args:
        results_dict (dict): Dictionary of {sheet_name: dataframe}
        filename (str): Output Excel filename
        output_dir (str): Directory to save the output file
    
    Returns:
        str: Path to the created file
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Full path for the output file
    filepath = os.path.join(output_dir, filename)
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        for sheet_name, results in results_dict.items():
            if isinstance(results, pd.DataFrame):
                df = results
            else:
                df = create_dataframe_from_results(results)
                
            if not df.empty:
                # Clean sheet name to be valid for Excel
                safe_sheet_name = str(sheet_name).replace('/', '_').replace('\\', '_')[:31]
                df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
    
    print(f"Exported data to {filepath}")
    return filepath
# Finnkode Data Fetcher

A tool for fetching and organizing medical code data from the Finnkode API, with special support for ICD-10 mental disorder codes (F00-F99).

## Project Structure

```
finnkode-fetcher/
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── client.py       # API client implementation
│   ├── models/
│   │   ├── __init__.py
│   │   └── code_types.py   # Constants and models for code types
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── export.py       # Data export utilities
│   │   └── logger.py       # Logging utilities
│   └── config.py           # Configuration settings
├── scripts/
│   ├── dataFetch.py        # Main script for fetching data
│   ├── fetch_mental_disorders.py  # Script for fetching mental disorder codes
│   └── visualize_disorders.py     # Script for visualizing mental disorder codes
└── tests/
    ├── __init__.py
    └── test_api_client.py  # Tests for API client
```

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/finnkode-fetcher.git
   cd finnkode-fetcher
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

## Usage

### Fetching Mental Disorder Codes (F00-F99)

To fetch all mental disorder codes:

```
python scripts/dataFetch.py --mental-disorders
```

Or use the dedicated script:

```
python scripts/fetch_mental_disorders.py
```

### Creating Visualizations

To create visualizations of mental disorder codes:

```
python scripts/visualize_disorders.py
```

This will create:
- Hierarchical visualization of code levels
- Bar charts of top-level categories
- Treemap visualization (requires `squarify` package)

### Advanced Usage

#### Fetching by Code Type and Category

```
python scripts/dataFetch.py --code-type icd10 --category V
```

#### Searching for Terms

```
python scripts/dataFetch.py --query "depression"
```

### Output Format Options

Export to CSV:

```
python scripts/dataFetch.py --mental-disorders --output-format csv
```

Export to Excel (default):

```
python scripts/dataFetch.py --mental-disorders --output-format excel
```

### Analyzing API Structure

To analyze and save raw API responses:

```
python scripts/dataFetch.py --analyze
```

### Additional Options

- `--output-dir, -o`: Specify output directory
- `--debug, -d`: Enable debug mode with more verbose output

## API Structure

The Finnkode API consists of two main endpoints:

1. **Search API**: `https://fs-elastic-prod.ent.westeurope.azure.elastic-cloud.com/api/as/v1/engines/ehelse-kodeverk-prod/search.json`
   - Used for general searching across all code types

2. **Hierarchy API**: `https://fat.kote.helsedirektoratet.no/api/code-systems/{code_system}/{category}/hierarchy`
   - Used for retrieving hierarchical code structures
   - Example: `/api/code-systems/icd10/V/hierarchy` retrieves mental disorder codes

## Mental Disorder Code Structure

The ICD-10 mental disorder codes (F00-F99) follow a hierarchical structure:

- Top level: Chapter V (Mental and behavioral disorders)
- Second level: Categories F00-F99
- Third level: Subcategories (e.g., F00.0, F00.1)
- Leaf nodes: Specific diagnoses

## Configuration

You can set API token and other settings in an `.env` file:

```
API_BEARER_TOKEN=your_bearer_token
```

Or modify the settings in `src/config.py`.

## Requirements

- Python 3.7+
- Required packages:
  - requests
  - pandas
  - tqdm
  - matplotlib
  - seaborn
  - openpyxl
  - python-dotenv
  - squarify (optional, for treemap visualization)

## Development

### Running Tests

```
python -m unittest discover -s tests
```

### Adding New Code Types

To add support for new medical code types, edit `src/models/code_types.py`.
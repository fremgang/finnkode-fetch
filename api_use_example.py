import requests

BASE_URL = "https://fat.kote.helsedirektoratet.no"  # Correct base URL

# Headers for Norwegian language (bokmål)
headers = {
    "Accept-Language": "nb",
    "Accept": "application/json"
}

def get_clinical_drugs(page_number=1, page_size=10):
    """
    Retrieve a list of clinical drugs (merkevarer) with pagination.
    """
    endpoint = f"{BASE_URL}/api/medicines/clinical-drugs"
    params = {
        "pageNumber": page_number,
        "pageSize": page_size,
        "includeBlacklistedItems": False
    }
    
    response = requests.get(endpoint, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 503:
        # Handle service unavailable due to cache refresh
        retry_after = response.headers.get('Retry-After', '60')
        print(f"Service temporarily unavailable. Retry after {retry_after} seconds.")
        return None
    else:
        print(f"Error: {response.status_code}")
        return None

def get_specific_clinical_drug(concept_id):
    """
    Retrieve a single clinical drug with the given concept ID.
    """
    endpoint = f"{BASE_URL}/api/medicines/clinical-drugs/{concept_id}"
    
    response = requests.get(endpoint, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        print(f"Clinical drug with concept ID {concept_id} not found.")
        return None
    elif response.status_code == 503:
        # Handle service unavailable due to cache refresh
        retry_after = response.headers.get('Retry-After', '60')
        print(f"Service temporarily unavailable. Retry after {retry_after} seconds.")
        return None
    else:
        print(f"Error: {response.status_code}")
        return None

def get_icd10_diagnoses(customer_code="hp", page_number=1, page_size=10):
    """
    Get a list of ICD-10 diagnoses filtered by customer preferences.
    """
    endpoint = f"{BASE_URL}/api/diagnosis/{customer_code}/icd10"
    params = {
        "pageNumber": page_number,
        "pageSize": page_size
    }
    
    response = requests.get(endpoint, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 400:
        print(f"Bad request. Invalid customer code: {customer_code}")
        return None
    else:
        print(f"Error: {response.status_code}")
        return None

def get_code_systems():
    """
    Return all available code systems with all endpoint URLs.
    """
    endpoint = f"{BASE_URL}/api/code-systems"
    
    response = requests.get(endpoint, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        return None

def get_codes_from_system(code_system, page_number=1, page_size=100, include_inactive=False):
    """
    Return all codes for a specified code system.
    
    code_system: One of "ICD10", "ICPC2", "NKPK", "PHBU", "NORPAT", "ANATOMISK", 
                 "TEKSTLIGERESULTATVERDIER", "PROVEMATERIALE", "NLK", "UNDERSOKELSESMETODE"
    """
    endpoint = f"{BASE_URL}/api/code-systems/{code_system}"
    params = {
        "pageNumber": page_number,
        "pageSize": page_size,
        "includeInactive": include_inactive
    }
    
    response = requests.get(endpoint, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 400:
        print(f"Bad request. Invalid code system: {code_system}")
        return None
    else:
        print(f"Error: {response.status_code}")
        return None

def download_code_system(code_system, file_type="JSON"):
    """
    Download a file with all codes in the specified code system.
    
    code_system: One of "ICD10", "ICPC2", "NKPK", "PHBU", "NORPAT", "ANATOMISK", 
                 "TEKSTLIGERESULTATVERDIER", "PROVEMATERIALE", "NLK", "UNDERSOKELSESMETODE"
    file_type: One of "JSON", "EXCEL", "TABULATOR", "SEMIKOLON", "PIPE", "XML"
    """
    endpoint = f"{BASE_URL}/api/code-systems/{code_system}/download/{file_type}"
    
    response = requests.get(endpoint, headers=headers)
    
    if response.status_code == 200:
        # Handle the file download
        file_name = f"{code_system}.{file_type.lower()}"
        with open(file_name, 'wb') as f:
            f.write(response.content)
        print(f"File downloaded as {file_name}")
        return file_name
    elif response.status_code == 400:
        print(f"Bad request. Invalid code system or file type.")
        return None
    elif response.status_code == 404:
        print(f"Code system not found: {code_system}")
        return None
    else:
        print(f"Error: {response.status_code}")
        return None

# Example usage
if __name__ == "__main__":
    # Get the first page of clinical drugs
    drugs = get_clinical_drugs(page_number=1, page_size=10)
    if drugs and drugs.get('data'):
        print(f"Retrieved {len(drugs['data'])} clinical drugs")
        # Print the name of the first drug
        if drugs['data']:
            print(f"First drug: {drugs['data'][0].get('termNorwegianSCT', {}).get('value', 'N/A')}")
    
    # Get a list of ICD-10 diagnoses
    diagnoses = get_icd10_diagnoses(customer_code="hp", page_number=1, page_size=10)
    if diagnoses and diagnoses.get('data'):
        print(f"Retrieved {len(diagnoses['data'])} ICD-10 diagnoses")
        # Print the name of the first diagnosis
        if diagnoses['data']:
            print(f"First diagnosis: {diagnoses['data'][0].get('termNorwegianSCT', {}).get('value', 'N/A')}")
    
    # Get available code systems
    code_systems = get_code_systems()
    if code_systems:
        print("Available code systems:")
        for system in code_systems:
            print(f"- {system.get('name', 'Unknown')}")
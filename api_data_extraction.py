import requests
import json
import csv
import os
from concurrent.futures import ThreadPoolExecutor
from time import sleep

BASE_URL = "https://fat.kote.helsedirektoratet.no"

headers = {
    "Accept-Language": "nb",
    "Accept": "application/json"
}

def fetch_all_pages(endpoint, params=None, max_pages=10):
    """Fetch all pages of data from a paginated endpoint"""
    if params is None:
        params = {}
    
    all_data = []
    current_page = params.get("pageNumber", 1)
    page_size = params.get("pageSize", 100)
    
    for page in range(current_page, current_page + max_pages):
        page_params = params.copy()
        page_params["pageNumber"] = page
        page_params["pageSize"] = page_size
        
        try:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, params=page_params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle different response structures
                if isinstance(data, dict) and "data" in data:
                    items = data["data"]
                    all_data.extend(items)
                    
                    # Check if we've reached the last page
                    total_pages = data.get("totalPages", 1)
                    if page >= total_pages:
                        break
                elif isinstance(data, list):
                    all_data.extend(data)
                    # No pagination info in list responses, so we'll stop when we get an empty list
                    if not data:
                        break
                else:
                    print(f"Unexpected response structure for {endpoint}")
                    break
                
                print(f"Fetched page {page} ({len(items)} items)")
            elif response.status_code == 503:
                # Service temporarily unavailable, might be refreshing cache
                retry_after = int(response.headers.get("Retry-After", "30"))
                print(f"Service unavailable, retrying after {retry_after} seconds")
                sleep(retry_after)
                page -= 1  # Retry this page
            else:
                print(f"Error fetching {endpoint} page {page}: {response.status_code}")
                break
                
        except Exception as e:
            print(f"Exception fetching {endpoint} page {page}: {str(e)}")
            break
            
    return all_data

def extract_clinical_drugs():
    """Extract and save clinical drugs data"""
    print("Extracting clinical drugs data...")
    drugs = fetch_all_pages("/api/medicines/clinical-drugs", {"pageSize": 100})
    
    if drugs:
        # Extract key information and save to CSV
        with open("clinical_drugs.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Concept ID", "Norwegian Term", "English Term", "Released", "VSO Applicable"])
            
            for drug in drugs:
                writer.writerow([
                    drug.get("conceptId", ""),
                    drug.get("termNorwegianSCT", {}).get("value", ""),
                    drug.get("termEnglishSCT", {}).get("value", ""),
                    drug.get("released", ""),
                    drug.get("vsoApplicable", "")
                ])
        
        # Save full data as JSON for further analysis
        with open("clinical_drugs.json", "w", encoding="utf-8") as f:
            json.dump(drugs, f, indent=2)
            
        print(f"Saved {len(drugs)} clinical drugs to clinical_drugs.csv and clinical_drugs.json")
    else:
        print("No clinical drugs data retrieved")

def extract_code_systems():
    """Extract available code systems"""
    print("Extracting code systems...")
    code_systems = requests.get(f"{BASE_URL}/api/code-systems", headers=headers).json()
    
    if code_systems:
        with open("code_systems.json", "w", encoding="utf-8") as f:
            json.dump(code_systems, f, indent=2)
        
        print(f"Saved {len(code_systems)} code systems to code_systems.json")
        return code_systems
    else:
        print("No code systems retrieved")
        return []

def extract_icd10_codes():
    """Extract ICD-10 diagnosis codes"""
    print("Extracting ICD-10 codes...")
    
    # Try common customer codes (may need adjustment based on actual API behavior)
    customer_codes = ["hp", "all", "general"]
    
    for code in customer_codes:
        try:
            diagnoses = fetch_all_pages(f"/api/diagnosis/{code}/icd10", {"pageSize": 100})
            
            if diagnoses:
                # Save to CSV
                with open(f"icd10_codes_{code}.csv", "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Concept ID", "Norwegian Term", "ICD-10 Code", "Released"])
                    
                    for diag in diagnoses:
                        icd10_code = ""
                        if "mapping" in diag and diag["mapping"]:
                            icd10_code = diag["mapping"][0].get("code", "")
                            
                        writer.writerow([
                            diag.get("conceptId", ""),
                            diag.get("termNorwegianSCT", {}).get("value", ""),
                            icd10_code,
                            diag.get("released", "")
                        ])
                
                # Save full data
                with open(f"icd10_codes_{code}.json", "w", encoding="utf-8") as f:
                    json.dump(diagnoses, f, indent=2)
                    
                print(f"Saved {len(diagnoses)} ICD-10 diagnoses with customer code '{code}'")
                return  # Exit after first successful extraction
                
            else:
                print(f"No ICD-10 diagnoses retrieved with customer code '{code}'")
                
        except Exception as e:
            print(f"Error extracting ICD-10 codes with customer code '{code}': {str(e)}")
    
    print("Failed to extract ICD-10 codes with any of the attempted customer codes")

def extract_icpc2_codes():
    """Extract ICPC-2 diagnosis codes"""
    print("Extracting ICPC-2 codes...")
    diagnoses = fetch_all_pages("/api/diagnosis/icpc2", {"pageSize": 100})
    
    if diagnoses:
        # Save to CSV
        with open("icpc2_codes.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Concept ID", "Norwegian Term", "ICPC-2 Code", "Released"])
            
            for diag in diagnoses:
                writer.writerow([
                    diag.get("conceptId", ""),
                    diag.get("termNorwegianSCT", {}).get("value", ""),
                    diag.get("icpc2Code", ""),
                    diag.get("released", "")
                ])
        
        # Save full data
        with open("icpc2_codes.json", "w", encoding="utf-8") as f:
            json.dump(diagnoses, f, indent=2)
            
        print(f"Saved {len(diagnoses)} ICPC-2 diagnoses")
    else:
        print("No ICPC-2 diagnoses retrieved")

def extract_fest_merkevarer():
    """Extract medication brands from FEST"""
    print("Extracting medication brands (merkevarer) from FEST...")
    response = requests.get(f"{BASE_URL}/api/fest/merkevarer", headers=headers)
    
    if response.status_code == 200:
        merkevarer = response.json()
        
        if merkevarer:
            # Save to CSV
            with open("fest_merkevarer.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Varenavn", "Produsent", "ATC Kode"])
                
                for merke in merkevarer:
                    writer.writerow([
                        merke.get("id", ""),
                        merke.get("varenavn", ""),
                        merke.get("produsent", ""),
                        merke.get("atcKode", "")
                    ])
            
            # Save full data
            with open("fest_merkevarer.json", "w", encoding="utf-8") as f:
                json.dump(merkevarer, f, indent=2)
                
            print(f"Saved {len(merkevarer)} merkevarer")
        else:
            print("No merkevarer retrieved")
    else:
        print(f"Error retrieving merkevarer: {response.status_code}")

def run_all_extractions():
    """Run all data extraction functions"""
    # Create output directory
    output_dir = "helsedir_api_data"
    os.makedirs(output_dir, exist_ok=True)
    os.chdir(output_dir)
    
    # List of extraction functions to run
    extraction_functions = [
        extract_clinical_drugs,
        extract_code_systems,
        extract_icd10_codes,
        extract_icpc2_codes,
        extract_fest_merkevarer
    ]
    
    # Run extractions in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(func) for func in extraction_functions]
        
        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"Error in extraction task: {str(e)}")
    
    print(f"\nAll extractions complete. Data saved to {output_dir}/")

if __name__ == "__main__":
    print("Starting medical data extraction from Helsedirektoratet API...")
    run_all_extractions()
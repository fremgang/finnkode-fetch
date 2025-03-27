"""
API client for interacting with the Finnkode API.
"""
import requests
import json
import time
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

class FinnkodeClient:
    """A client for fetching medical code data from the Finnkode API."""
    
    # Base URLs
    SEARCH_BASE_URL = "https://fs-elastic-prod.ent.westeurope.azure.elastic-cloud.com/api/as/v1/engines/ehelse-kodeverk-prod/search.json"
    HIERARCHY_BASE_URL = "https://fat.kote.helsedirektoratet.no/api/code-systems"
    
    def __init__(self, bearer_token=None):
        """
        Initialize the API client.
        
        Args:
            bearer_token (str, optional): Authentication token for the API. 
                Defaults to the public token if None.
        """
        self.bearer_token = bearer_token or "search-osdi3rea1ywr1tzff78z75ti"
        self.search_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "authorization": f"Bearer {self.bearer_token}",
            "content-type": "application/json",
            "x-elastic-client-meta": "ent=8.9.0-legacy,js=browser,t=8.9.0-legacy,ft=universal",
            "x-swiftype-client": "elastic-app-search-javascript",
            "x-swiftype-client-version": "8.9.0",
            "Origin": "https://finnkode.helsedirektoratet.no",
            "Connection": "keep-alive"
        }
        
        self.hierarchy_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:136.0) Gecko/20100101 Firefox/136.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Origin": "https://finnkode.helsedirektoratet.no",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site"
        }
        
        self.search_session = requests.Session()
        self.search_session.headers.update(self.search_headers)
        
        self.hierarchy_session = requests.Session()
        self.hierarchy_session.headers.update(self.hierarchy_headers)
    
    def search(self, query="", filters=None, page=1, per_page=20):
        """
        Search the Finnkode database with a specific query using the Elastic Search API.
        
        Args:
            query (str): The search query term
            filters (dict, optional): Dictionary of filters to apply
            page (int, optional): Page number for pagination
            per_page (int, optional): Results per page
            
        Returns:
            dict: JSON response from the API
        """
        payload = {
            "query": query,
            "page": {
                "size": per_page,
                "current": page
            }
        }
        
        # Only add filters if they exist
        if filters:
            payload["filters"] = filters
        
        try:
            response = self.search_session.post(self.SEARCH_BASE_URL, json=payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None
    
    def get_code_system_hierarchy(self, code_system="icd10", category=None, code=None):
        """
        Get the hierarchy for a specific code system, category, or code.
        
        Args:
            code_system (str): The code system (e.g., "icd10", "icpc2")
            category (str, optional): The category within the code system (e.g., "V" for mental disorders in ICD-10)
            code (str, optional): A specific code within the category
            
        Returns:
            dict: JSON response containing the hierarchy
        """
        # Build the URL based on the provided parameters
        url_parts = [self.HIERARCHY_BASE_URL, code_system.lower()]
        
        if category:
            url_parts.append(category)
            
            if code:
                url_parts.append(code)
                
        url_parts.append("hierarchy")
        url = "/".join(url_parts)
        
        try:
            response = self.hierarchy_session.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None
    
    def get_icd10_mental_disorders(self):
        """
        Get all ICD-10 mental disorders (F00-F99).
        
        Returns:
            dict: JSON response containing mental disorders
        """
        # Mental disorders are in category V of ICD-10
        return self.get_code_system_hierarchy("icd10", "V")
    
    def get_icd10_codes_by_chapter(self, chapter_code):
        """
        Get ICD-10 codes for a specific chapter.
        
        Args:
            chapter_code (str): The chapter code (e.g., "I", "V", "X")
            
        Returns:
            dict: JSON response containing the codes
        """
        return self.get_code_system_hierarchy("icd10", chapter_code)
    
    def get_icd10_chapter_list(self):
        """
        Get the list of all ICD-10 chapters.
        
        Returns:
            dict: JSON response containing the chapters
        """
        return self.get_code_system_hierarchy("icd10")
    
    def get_detailed_code_info(self, code_system="icd10", code=None):
        """
        Get detailed information about a specific code.
        
        Args:
            code_system (str): The code system (e.g., "icd10", "icpc2")
            code (str): The specific code to get details for
            
        Returns:
            dict: JSON response containing the code details
        """
        if not code:
            return None
            
        url = f"{self.HIERARCHY_BASE_URL}/{code_system.lower()}/{code}"
        
        try:
            response = self.hierarchy_session.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                return None
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return None
    
    def _extract_f_codes_recursive(self, data, f_codes=None):
        """
        Recursively extract all F codes from the hierarchy.
        
        Args:
            data (dict): The hierarchy data
            f_codes (list, optional): List to store the extracted F codes
            
        Returns:
            list: List of all F codes
        """
        if f_codes is None:
            f_codes = []
            
        # Check if this is a code starting with F
        if isinstance(data, dict) and 'codeValue' in data:
            code_value = data['codeValue']
            if code_value.startswith('F') and len(code_value) > 1:  # Ensure it's not just "F" itself
                f_codes.append(data)
                
        # Check children recursively
        if isinstance(data, dict) and 'children' in data and data['children']:
            for child in data['children']:
                self._extract_f_codes_recursive(child, f_codes)
                
        return f_codes
    
    def extract_mental_disorder_codes(self, hierarchy_data):
        """
        Extract all mental disorder codes (F00-F99) from the hierarchy.
        
        Args:
            hierarchy_data (dict): The hierarchy data from get_icd10_mental_disorders()
            
        Returns:
            list: List of all mental disorder codes
        """
        return self._extract_f_codes_recursive(hierarchy_data)
    
    def fetch_all_mental_disorder_codes(self):
        """
        Fetch all mental disorder codes (F00-F99) and extract them.
        
        Returns:
            list: List of all mental disorder codes
        """
        hierarchy_data = self.get_icd10_mental_disorders()
        if not hierarchy_data:
            return []
            
        return self.extract_mental_disorder_codes(hierarchy_data)
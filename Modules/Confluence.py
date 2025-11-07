"""
Confluence API Integration Module

This module provides a client for interacting with Confluence pages via the REST API.
It enables fetching page content, parsing HTML tables to extract team member information,
and retrieving user details based on Confluence user keys.

Main functionality:
- Fetch and parse Confluence page content
- Extract responsible persons from structured HTML tables
- Resolve Confluence user keys to usernames
- Search for specific roles (e.g., Main Developer) using keyword matching

Dependencies:
    - bs4 (BeautifulSoup4): For HTML parsing
    - requests: For HTTP API calls
    - typing: For type hints

Example:
    >>> api = MyConfluenceAPI(
    ...     confluence_api_key="your-api-token",
    ...     confluence_page="https://confluence.example.com",
    ...     sub_page_name="195_App"
    ... )
    >>> developer = api.get_main_developer()
    >>> print(developer)
    'Oleksandr'
"""
from bs4 import BeautifulSoup
from typing import Optional, List
import requests


class MyConfluenceAPI:
    """
    A client for interacting with Confluence pages and extracting structured information.

    This class provides methods to fetch Confluence page content, parse HTML tables
    to find responsible persons for various roles, and resolve user keys to usernames.

    Attributes:
        sub_page_name (str): The Confluence page identifier/path
        body (Optional[str]): The HTML content of the Confluence page
        confluence_api_key (str): Bearer token for Confluence API authentication
        confluence_page (str): Base URL of the Confluence instance

    Example:
        >>> api = MyConfluenceAPI(
        ...     confluence_api_key="abc123",
        ...     confluence_page="https://confluence.company.com",
        ...     sub_page_name="195_App"
        ... )
        >>> developer = api.get_main_developer()
    """

    def __init__(self,
                 confluence_api_key: str,
                 confluence_page: str,
                 sub_page_name: str) -> None:
        """
        Initialize the Confluence API client.

        Args:
            confluence_api_key: Bearer token for API authentication
            confluence_page: Base URL of the Confluence instance (e.g., "https://confluence.example.com")
            sub_page_name: Page identifier or path within Confluence

        Note:
            The page body is fetched immediately upon initialization via get_page_body().
        """
        self.sub_page_name: str = sub_page_name
        # Store API credentials
        self.confluence_api_key = confluence_api_key
        self.confluence_page = confluence_page
        # Fetch page content immediately upon initialization
        self.body: Optional[str] = self.get_page_body()

    def get_page_body(self) -> Optional[str]:
        """Fetch the HTML content of the Confluence page."""
        if not self.confluence_page or not self.confluence_api_key:
            raise ValueError("Confluence URL or API key not configured.")

        try:
            response = requests.get(
                f'{self.confluence_page}/{self.sub_page_name}',  # Fixed: use confluence_page
                headers={'Authorization': f'Bearer {self.confluence_api_key}'},
                timeout=10
            )
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch Confluence page: {e}")

    def get_person_responsible_by_keywords(self, list_key_words: List[str]) -> Optional[str]:
        """
        Find the username of a person responsible by searching for keyword matches.

        Iterates through a list of keywords (e.g., role names) and returns the username
        of the first person found matching any keyword in the page's HTML tables.

        Args:
            list_key_words: List of search terms to look for in table headers
                           (e.g., ["Developer:", "Main Developer:"])

        Returns:
            The username of the responsible person if found, None otherwise.

        Note:
            This method searches in order and returns the first match found.
        """
        # Try each keyword until a match is found
        for key_word in list_key_words:
            person_api_key = self.get_person_responsible(self.body, key_word)
            if person_api_key:
                # Resolve user key to readable username
                return self.get_username_by_user_key(person_api_key)
        return None

    def get_main_developer(self) -> Optional[str]:
        """
        Retrieve the username of the main developer from the Confluence page.

        Convenience method that searches for common developer role keywords
        in the page content.

        Returns:
            The username of the main developer if found, None otherwise.

        Example:
            >>> api = MyConfluenceAPI(...)
            >>> developer = api.get_main_developer()
            >>> print(developer)
            'jane.smith'
        """
        # Define common variations of developer role labels
        list_key_words: List[str] = ['Developer:', 'Main Developer:']
        return self.get_person_responsible_by_keywords(list_key_words)

    def get_username_by_user_key(self, user_key: str) -> Optional[str]:
        """
        Resolve a Confluence user key to a readable username.

        Makes an API call to Confluence's user endpoint to retrieve user details
        and extract the username field.

        Args:
            user_key: Confluence internal user identifier (e.g., "ff8080814a1b2c3d")

        Returns:
            The username associated with the user key, or 'Username not found' if
            the username field is missing in the API response.

        Raises:
            ValueError: If Confluence configuration is missing or if the API request fails.

        Example:
            >>> api = MyConfluenceAPI(...)
            >>> username = api.get_username_by_user_key("ff8080814a1b2c3d")
            >>> print(username)
            'john.doe'
        """
        # Validate required configuration
        if not self.confluence_page or not self.confluence_api_key:
            raise ValueError("Confluence configuration missing.")

        # Construct user lookup endpoint
        url = f"{self.confluence_page}/rest/api/latest/user?key={user_key}"
        headers = {
            "Authorization": f"Bearer {self.confluence_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            # Request user details from Confluence API
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            # Extract username from JSON response, with fallback message
            return response.json().get('username', 'Username not found')
        except requests.RequestException as e:
            raise ValueError(f"Failed to get username for key {user_key}: {e}")

    @staticmethod
    def get_person_responsible(html_string: Optional[str], person_type: str) -> Optional[str]:
        """
        Extract a person's user key from an HTML table based on role label.

        Parses HTML content to find a table header matching the person_type,
        then extracts the Confluence user key from the adjacent table cell.

        Args:
            html_string: HTML content containing the table structure
            person_type: The role label to search for (e.g., "Developer:", "Project Owner:")

        Returns:
            The Confluence user key (ri:userkey attribute) if found, None otherwise.

        Raises:
            ValueError: If HTML parsing fails or expected structure is malformed.

        Example:
            >>> html = '<table><tr><th>Developer:</th><td><ri:user ri:userkey="abc123"/></td></tr></table>'
            >>> key = MyConfluenceAPI.get_person_responsible(html, "Developer:")
            >>> print(key)
            'abc123'

        Note:
            This method expects Confluence's specific HTML structure with <ri:user>
            elements containing ri:userkey attributes.
        """
        # Handle empty input
        if not html_string:
            return None

        try:
            # Parse HTML content
            soup = BeautifulSoup(html_string, 'html.parser')

            # Find the table header matching the person type
            th_element = soup.find('th', string=person_type)
            if not th_element:
                return None

            # Get the adjacent table cell
            td_element = th_element.find_next_sibling('td')
            if not td_element:
                return None

            # Extract user key from Confluence's custom ri:user element
            user_element = td_element.find('ri:user')
            if user_element and 'ri:userkey' in user_element.attrs:
                return user_element['ri:userkey']
            return None
        except (AttributeError, KeyError) as e:
            raise ValueError(f"Error parsing HTML for {person_type}: {e}")

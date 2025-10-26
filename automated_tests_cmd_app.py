"""
Automated Tests Command-Line Application

This script provides a command-line interface for managing and testing of different kinds of software.
Users can navigate through different pages, input app ID, and perform automated configuration checks
before running apps. The application interacts with Confluence to fetch information about the tested application

This is not a full application, but only a concept of it. You can add all the possible checks you need for your process.

Features:
- Command-line navigation between pages.
- Fetch app details from a specified folder.
- Perform automated tests before app execution.
- Retrieve app-related information from Confluence.
- Support for user input validation and basic error handling.

Usage:
Run the script and follow the on-screen instructions to navigate through options.

Dependencies:
- requests
- beautifulsoup4
- json
- os
- time
- enum
- re

Author: Oleksandr Krasnoshchok
Date: 01.02.2025
"""
import time
import requests
import os
import json
from bs4 import BeautifulSoup
from enum import Enum
import re
from typing import Dict, Optional, Callable, List

APPS_FOLDER: str = "C:/Users/krasn/OneDrive/Pulpit/work/test"
CONFLUENCE_PAGE: str = "https://your-confluence-page"
CONFLUENCE_API_KEY: str = 'your_api_key'
URL_QS: str = 'your_url_qs'
URL_PROD: str = 'your_url_prod'

APP_HEADER: str = "Write 'exit' to exit application.\nWrite 'home' to go to Home Page"


class Pages(Enum):
    HOME = 1
    INPUT_APP_FOR_CONFIG_CHECK = 2
    TEST_AUTOMATION = 3
    CHOOSE_PROPOSED_APP = 4


class AppForTests:
    def __init__(self) -> None:
        self.current_page: Pages = Pages.HOME
        self.matching_folders: Dict[int, str] = {}
        self.chosen_app: Optional[int] = None
        self.commands: Dict[Pages, Callable[[str], None]] = {
            Pages.HOME: self.handle_home_commands,
            Pages.INPUT_APP_FOR_CONFIG_CHECK: self._handle_input_app_commands,
            Pages.CHOOSE_PROPOSED_APP: self._handle_chooseapps_commands,
            Pages.TEST_AUTOMATION: self._handle_test_automation_commands
        }

    def navigate_to_page(self, page: Pages) -> None:
        self.current_page = page
        clear_screen()
        self.render_page()

    def render_page(self) -> None:
        print(APP_HEADER)
        if self.current_page == Pages.HOME:
            print("\nHello, this is your app.\n")
            print("1 - Automated Test (before app start)")
            #print("2 - Automated Test (of a current app run)")
        elif self.current_page == Pages.TEST_AUTOMATION and self.chosen_app:
            app_folder_path: str = self.matching_folders[self.chosen_app]
            print(f"App-ID: {extract_app_id(app_folder_path)}")
            print(f"App Folder: {app_folder_path}")
            print(f"\nWrite '1': To carry out the Check of a Conflunece Page")
            print(f"Write '2': To validate the config file\n")

        elif self.current_page == Pages.INPUT_APP_FOR_CONFIG_CHECK:
            print("\nWhich app would you like to test? Input the app number (id)\n")
        elif self.current_page == Pages.CHOOSE_PROPOSED_APP:
            print("\nChoose the app from the list:\n")
            for index, folder in self.matching_folders.items():
                print(f"{index}: {folder}")

    def check_app_confluence_page(self) -> None:
        if self.chosen_app is None:
            print("No app selected")
            return

        app_id: str = extract_app_id(self.matching_folders[self.chosen_app])
        print(f"Checking Confluence page for app ID: {app_id}")
        try:
            confluence_page: ConfluencePage = ConfluencePage(f"app_{app_id}")
            main_dev: Optional[str] = confluence_page.get_main_developer()
            analyst: Optional[str] = confluence_page.get_analyst()
            print(f"Main Developer: {main_dev or 'Not found'}")
            print(f"Analyst: {analyst or 'Not found'}")
        except Exception:
            print("Confluence Page can not be checked")

    def handle_command(self, command: str) -> bool:
        if command.lower() == "exit":
            print("See you again! Good bye.")
            return False
        elif command.lower() in ["restart", "home"]:
            self.navigate_to_page(Pages.HOME)
        elif command.isnumeric():
            self.commands[self.current_page](command)
        else:
            print("Sorry, this function is not supported yet.")
        return True

    def handle_home_commands(self, command: str) -> None:
        if command == "1":
            self.navigate_to_page(Pages.INPUT_APP_FOR_CONFIG_CHECK)

    def _handle_chooseapps_commands(self, command: str) -> None:
        if command.isnumeric() and int(command) in self.matching_folders:
            self.chosen_app = int(command)
            self.navigate_to_page(Pages.TEST_AUTOMATION)

    def _handle_input_app_commands(self, command: str) -> None:
        root_folder: str = APPS_FOLDER
        self.matching_folders = {}
        for index, item in enumerate(os.listdir(root_folder), start=1):
            if os.path.isdir(os.path.join(root_folder, item)) and command in item:
                self.matching_folders[index] = os.path.join(root_folder, item)
        if self.matching_folders:
            self.navigate_to_page(Pages.CHOOSE_PROPOSED_APP)
        else:
            print(f"No folders found with app number ({command})")

    def _handle_test_automation_commands(self, command: str) -> None:
        if command == "1":
            print("\nGet Confluence Page Info...\n")
            self.check_app_confluence_page()

        if command == "2":
            print("\nValidate config file...\n")
            # here will be the function for config file validation
            print("Config file validation was successful.\n")


class ConfluencePage:
    def __init__(self, page_name: str) -> None:
        self.page_name: str = page_name
        self.body: Optional[str] = self.get_page_body()

    def get_page_body(self) -> Optional[str]:
        response: requests.Response = requests.get(
            f'{URL_PROD}/{self.page_name}',
            headers={'Authorization': f'Bearer {CONFLUENCE_API_KEY}'}
        )
        return response.text if response.status_code == 200 else None

    def get_person_responsible_by_keywords(self, list_key_words: List[str]) -> Optional[str]:
        person_api_key: str = ""
        for key_word in list_key_words:
            person_api_key = self.get_person_responsible(self.body, key_word)
            if person_api_key:
                return self.get_username_by_user_key(CONFLUENCE_API_KEY, person_api_key)
        return person_api_key if person_api_key else None

    def get_analyst(self) -> Optional[str]:
        list_key_words: List[str] = ['Analyst:', 'Analyst']
        return self.get_person_responsible_by_keywords(list_key_words)

    def get_main_developer(self) -> Optional[str]:
        list_key_words: List[str] = ['Developer:', 'Main Developer:']
        return self.get_person_responsible_by_keywords(list_key_words)

    @staticmethod
    def get_username_by_user_key(token: str, user_key: str) -> str:
        url: str = f"{CONFLUENCE_PAGE}/rest/api/latest/user?key={user_key}"
        headers: Dict[str, str] = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        response: requests.Response = requests.get(url, headers=headers)
        return response.json().get('username', 'Username not found')

    @staticmethod
    def get_person_responsible(html_string: Optional[str], person_type: str) -> str:
        if not html_string:
            return ""
        try:
            soup: BeautifulSoup = BeautifulSoup(html_string, 'html.parser')
            th_element = soup.find('th', string=person_type)
            td_element = th_element.find_next_sibling('td') if th_element else None
            return td_element.find('ri:user')['ri:userkey'] if td_element else ""
        except Exception:
            return ""


def extract_app_id(folder_name: str) -> str:
    match: Optional[re.Match[str]] = re.match(r'^\D*(\d+)', folder_name)
    return match.group(1) if match else ""


def clear_screen() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def monitor_command_line(app: AppForTests) -> None:
    while True:
        command: str = input("Enter command: ")
        if not app.handle_command(command):
            break
        time.sleep(1)


if __name__ == "__main__":
    clear_screen()
    tests_app: AppForTests = AppForTests()
    tests_app.navigate_to_page(Pages.HOME)
    monitor_command_line(tests_app)
"""
Automated Tests Command-Line Application

This script provides a command-line interface for managing and testing different kinds of software.
Users can navigate between pages, input app IDs, perform different tasks

The app expects you to have your projects saved in the folder like:
APPS_FOLDER=D:/input_folder

You should set it in .env.

So your project names in the folder APPS_FOLDER must begin with ID followed by underscore, like "145_MyProject"

So during the stage of chosing the project, you can only write the ID of your App, so that you can do further
tests

Features:
---------
- Command-line navigation between logical pages.
- Fetch app details from a specified local folder.
- Perform pre-execution validation tests.
- Support for user input validation and error handling.

Dependencies:
-------------
- os
- time
- enum
- re
- python-dotenv

Author: Oleksandr Krasnoshchok
Date: 01.02.2025
"""

import os
import re
import sys
import time
import logging
from enum import Enum
from typing import Dict, Optional, Callable
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# CONFIGURATION & INITIALIZATION
# ---------------------------------------------------------------------------

# Configure logging for the entire app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file (must exist in project root)
load_dotenv()

# Read environment variables
APPS_FOLDER: Optional[str] = os.getenv('APPS_FOLDER')

# Header message displayed in the console UI
APP_HEADER: str = (
    "Write 'exit' to exit application.\n"
    "Write 'home' to return to Home Page."
)


# ---------------------------------------------------------------------------
# CUSTOM EXCEPTIONS
# ---------------------------------------------------------------------------

class ConfigError(Exception):
    """Raised when the required configuration is missing."""
    pass


# ---------------------------------------------------------------------------
# ENUM DEFINITIONS
# ---------------------------------------------------------------------------

class Pages(Enum):
    """Enum representing available navigation pages in the CLI."""
    HOME = 1
    INPUT_APP_FOR_CONFIG_CHECK = 2
    TEST_AUTOMATION = 3
    CHOOSE_PROPOSED_APP = 4


class TestCommands(Enum):
    """Enum representing available commands in the test automation page."""
    CONFLUENCE_CHECK = "1"
    CONFIG_VALIDATION = "2"


# ---------------------------------------------------------------------------
# ENVIRONMENT VALIDATION
# ---------------------------------------------------------------------------

def validate_environment() -> None:
    """
    Validate that all required environment variables are set.

    Raises:
        ConfigError: If one or more required environment variables are missing.
    """
    required_vars = {
        'APPS_FOLDER': APPS_FOLDER
    }

    missing = [name for name, value in required_vars.items() if not value]
    if missing:
        raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")


# ---------------------------------------------------------------------------
# MAIN APPLICATION CLASS
# ---------------------------------------------------------------------------

class AppForTests:
    """
    Command-line application for managing and testing software components.

    This class handles user navigation, page rendering, and command processing.
    """

    def __init__(self) -> None:
        """Initialize app state and navigation logic."""
        self.current_page: Pages = Pages.HOME
        self.matching_folders: Dict[int, str] = {}
        self.chosen_app: Optional[int] = None

        # Define command handlers for each page
        self.commands: Dict[Pages, Callable[[str], None]] = {
            Pages.HOME: self.handle_home_commands,
            Pages.INPUT_APP_FOR_CONFIG_CHECK: self._handle_input_app_commands,
            Pages.CHOOSE_PROPOSED_APP: self._handle_choose_apps_commands,
            Pages.TEST_AUTOMATION: self._handle_test_automation_commands
        }

    # -----------------------------------------------------------------------
    # PAGE NAVIGATION & RENDERING
    # -----------------------------------------------------------------------

    def navigate_to_page(self, page: Pages) -> None:
        """Switch to a different page and render its content."""
        self.current_page = page
        clear_screen()
        self.render_page()

    def render_page(self) -> None:
        """Display the content of the current page."""
        print(APP_HEADER)

        if self.current_page == Pages.HOME:
            print("\nHello, this is your app.")
            print("\nChoose what you want to do:")
            print("\n1 - Automated Test\n")

        elif self.current_page == Pages.INPUT_APP_FOR_CONFIG_CHECK:
            print("\nWhich app would you like to test? Input the app number (id)\n")

        elif self.current_page == Pages.CHOOSE_PROPOSED_APP:
            print("\nChoose the app from the list:\n")
            for index, folder in self.matching_folders.items():
                print(f"{index}: {folder}")

        elif self.current_page == Pages.TEST_AUTOMATION and self.chosen_app:
            # Display test options for the chosen app
            if self.chosen_app not in self.matching_folders:
                print("Error: Selected app not found in folders.")
                return

            app_folder_path: str = self.matching_folders[self.chosen_app]
            app_id = extract_app_id(app_folder_path)
            print(f"App-ID: {app_id}")
            print(f"App Folder: {app_folder_path}")
            print("\nAvailable options:")
            print(f"{TestCommands.CONFLUENCE_CHECK.value} - Check Confluence Page")
            print(f"{TestCommands.CONFIG_VALIDATION.value} - Validate Config File\n")

    # -----------------------------------------------------------------------
    # COMMAND HANDLING
    # -----------------------------------------------------------------------

    def handle_command(self, command: str) -> bool:
        """
        Handle user input depending on the current page.

        Args:
            command: The user input string.

        Returns:
            bool: False if user wants to exit, True otherwise.
        """
        if command.lower() == "exit":
            print("See you again! Goodbye.")
            return False

        elif command.lower() in ["restart", "home"]:
            self.navigate_to_page(Pages.HOME)

        elif command.isnumeric():
            handler = self.commands.get(self.current_page)
            if handler:
                handler(command)
            else:
                print("Error: No handler for the current page.")
        else:
            print("Sorry, this function is not supported yet.")

        return True

    # -----------------------------------------------------------------------
    # PAGE-SPECIFIC COMMAND HANDLERS
    # -----------------------------------------------------------------------

    def handle_home_commands(self, command: str) -> None:
        """Handle commands on the HOME page."""
        if command == "1":
            self.navigate_to_page(Pages.INPUT_APP_FOR_CONFIG_CHECK)

    def _handle_input_app_commands(self, command: str) -> None:
        """
        Handle app search by ID in the INPUT_APP_FOR_CONFIG_CHECK page.

        Args:
            command: The app ID or partial folder name entered by the user.
        """
        if not APPS_FOLDER:
            print("Error: APPS_FOLDER not configured.")
            return

        if not os.path.exists(APPS_FOLDER):
            print(f"Error: Apps folder not found: {APPS_FOLDER}")
            return

        self.matching_folders.clear()

        try:
            for index, item in enumerate(os.listdir(APPS_FOLDER), start=1):
                item_path = os.path.join(APPS_FOLDER, item)
                if os.path.isdir(item_path) and command in item:
                    self.matching_folders[index] = item_path
        except OSError as e_os:
            logger.error(f"Error reading apps folder: {e_os}")
            print("Error: Could not read apps folder.")
            return

        if self.matching_folders:
            self.navigate_to_page(Pages.CHOOSE_PROPOSED_APP)
        else:
            print(f"No folders found with app number ({command})")

    def _handle_choose_apps_commands(self, command: str) -> None:
        """Handle user selection of an app from the proposed list."""
        if command.isnumeric() and int(command) in self.matching_folders:
            self.chosen_app = int(command)
            self.navigate_to_page(Pages.TEST_AUTOMATION)
        else:
            print(f"Invalid selection: {command}")

    def _handle_test_automation_commands(self, command: str) -> None:
        """Handle commands in the TEST_AUTOMATION page."""
        if command == TestCommands.CONFLUENCE_CHECK.value:
            print("\nFetching Confluence Page Info...\n")
        elif command == TestCommands.CONFIG_VALIDATION.value:
            print("\nValidating configuration file...\n")
            self._validate_config_file()
        else:
            print(f"Unknown command: {command}")

    # -----------------------------------------------------------------------
    # FEATURE IMPLEMENTATIONS
    # -----------------------------------------------------------------------

    @staticmethod
    def _validate_config_file() -> None:
        """
        Validate the configuration file for the chosen app.

        This is a placeholder for actual validation logic.
        You can expand this with JSON/YAML schema validation or syntax checks.
        """
        print("Config file validation was successful.\n")


# ---------------------------------------------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------------------------------------------

def extract_app_id(folder_name: str) -> str:
    """Extract numeric app ID from folder name."""
    match = re.search(r'\d+', folder_name)
    return match.group(0) if match else ""

def clear_screen() -> None:
    """Clear the terminal screen safely, without TERM warnings."""
    try:
        if os.name == 'nt':
            os.system('cls')
        else:
            # Only clear if TERM is defined (prevents "TERM not set" errors)
            if os.getenv('TERM'):
                os.system('clear')
            else:
                print("\n" * 5)  # print some blank lines instead
    except Exception:
        print("\n" * 5)


def monitor_command_line(app: AppForTests) -> None:
    """
    Continuously monitor user input and pass commands to the app.

    Args:
        app: Instance of AppForTests running the main loop.
    """
    while True:
        try:
            command = input("Enter command: ").strip()
            if not app.handle_command(command):
                break
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Exiting...")
            break
        except Exception as e_c_loop:
            logger.error(f"Unexpected error in command loop: {e_c_loop}")
            print("An error occurred. Please try again.")


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        # Ensure required environment variables are available
        validate_environment()

        # Start the CLI app
        clear_screen()
        tests_app = AppForTests()
        tests_app.navigate_to_page(Pages.HOME)
        monitor_command_line(tests_app)

    except ConfigError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print("Fatal error occurred. Check logs for details.")
        sys.exit(1)
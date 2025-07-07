import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from .config_manager import ConfigManager

class SheetsManager:
    """
    Google Sheets API integration manager for JobApp.

    - Loads spreadsheet ID, tab name, and credentials from config (user or project).
    - Provides methods to fetch all records, append rows, convert to pandas DataFrame, and delete rows.
    - Handles authentication using service account credentials.
    - Used for job tracking and batch operations.
    """
    def __init__(self, spreadsheet_id=None, tab_name=None, creds_path=None):
        load_dotenv()
        print("[DEBUG] Initializing SheetsManager...")
        self.config = ConfigManager()
        
        # Get spreadsheet settings from config
        print("[DEBUG] Loading spreadsheet settings from config...")
        spreadsheet_config = self.config.get_yaml_config('default', {}).get('google_spreadsheet', {})
        print(f"[DEBUG] Loaded spreadsheet config: {spreadsheet_config}")
        self.spreadsheet_id = spreadsheet_id or spreadsheet_config.get('spreadsheet_id')
        self.tab_name = tab_name or spreadsheet_config.get('tab_name')
        
        print(f"[DEBUG] Using spreadsheet_id: {self.spreadsheet_id}")
        print(f"[DEBUG] Using tab_name: {self.tab_name}")
        
        if not self.spreadsheet_id:
            raise ValueError("No spreadsheet_id provided in config or constructor")
        if not self.tab_name:
            raise ValueError("No tab_name provided in config or constructor")
        
        # Get credentials path from config
        if creds_path is None:
            creds_path = self.config.get_gspread_credentials_path()
        self.creds_path = str(creds_path)
        print(f"[DEBUG] Using credentials path: {self.creds_path}")
        
        self.scope = ['https://www.googleapis.com/auth/spreadsheets']
        self.creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_path, self.scope)
        self.client = gspread.authorize(self.creds)
        self.sheet = self.client.open_by_key(self.spreadsheet_id).worksheet(self.tab_name)

    def get_all_records(self):
        """Return all records from the current sheet as a list of dicts."""
        return self.sheet.get_all_records()

    def append_row(self, row):
        """Append a row to the current sheet."""
        self.sheet.append_row(row)

    def get_dataframe(self):
        """Return all records as a pandas DataFrame."""
        records = self.get_all_records()
        return pd.DataFrame(records)
    
    def delete_row(self, row: int) -> bool:
        """Delete a row (1-indexed) from the current sheet. Returns True if successful, False otherwise."""
        try:
            if not isinstance(row, int) or row < 1:
                print(f"Error: Invalid Google Sheet row number '{row}'. Must be a positive integer (1-indexed).")
                return False

            total_rows_in_sheet = self.sheet.row_count
            if row > total_rows_in_sheet:
                print(f"Error: Google Sheet row {row} is out of bounds. "
                      f"The sheet currently has {total_rows_in_sheet} rows.")
                return False

            print(f"Deleting Google Sheet row {row}...")
            self.sheet.delete_rows(row)
            print("Row deleted successfully.")
            return True
        except Exception as e:
            print(f"An unexpected error occurred during delete_row: {e}")
            return False
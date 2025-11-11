from helpers.config import get_settings, Settings
from pathlib import Path
import random
import string
import re

class BaseController:
    def __init__(self):
        self.app_settings = get_settings()
        self.rel_asset_files_path: Path = Path("assets/files")
        self.abs_asset_files_path: Path = self.rel_asset_files_path.resolve()
        print(str(self.abs_asset_files_path))
        
    def get_clean_filename(self, orig_filename: str) -> str:
        # remove any special characters, except underscore and .
        cleaned_file_name = re.sub(r'[^\w.]', '', orig_filename.strip())

        # replace spaces with underscore
        cleaned_file_name = cleaned_file_name.replace(" ", "_")

        return cleaned_file_name
        
    def generate_random_string(self, length: int=12):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
from helpers.config import get_settings, Settings
from pathlib import Path
import random
import string
import re


class BaseController:
    def __init__(self) -> None:
        self.app_settings: Settings = get_settings()
        backend_dir = self.app_settings.DB_BACKEND.lower()
        self.rel_asset_files_path: Path = Path("assets") / backend_dir / "files"
        self.abs_asset_files_path: Path = self.rel_asset_files_path.resolve()

    def get_clean_filename(self, orig_filename: str) -> str:
        # remove any special characters, except underscore and .
        cleaned_file_name = re.sub(r'[^\w.]', '', orig_filename.strip())

        # replace spaces with underscore
        cleaned_file_name = cleaned_file_name.replace(" ", "_")

        return cleaned_file_name

    def generate_random_string(self, length: int = 12):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

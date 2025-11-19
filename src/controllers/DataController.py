from typing import Literal
from controllers.BaseController import BaseController
from models import ResponseSignals
from fastapi import UploadFile
from pathlib import Path


class DataController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.size_scale = 1048576

    def validate_uploaded_file(self, file: UploadFile):
        if file.content_type not in self.app_settings.FILE_ALLOWED_TYPES:
            return False, ResponseSignals.FILE_TYPE_NOT_SUPPORTED.value

        if file.size > self.app_settings.FILE_MAX_SIZE * self.size_scale:
            return False, ResponseSignals.FILE_SIZE_EXCEEDED.value

        return True, ResponseSignals.FILE_VALIDATED_SUCCESS.value

    def generate_unique_filename(self, orig_file_name: str, orig_file_path: Path) -> str:
        # 1. generate random key
        random_key: str = self.generate_random_string()

        # 2. clean orig_file_name
        cleaned_filename: str = self.get_clean_filename(orig_filename=orig_file_name)

        # 3. concate key with clean name
        final_filename = random_key + "_" + cleaned_filename

        # 4. check if the final name exists in project path
        final_path: Path = orig_file_path / final_filename

        # 5. check if the new file name exist, if it exist generate new key. Otherwise return it
        while final_path.exists():
            random_key: str = self.generate_random_string()
            final_filename = random_key + "_" + cleaned_filename
            final_path: Path = orig_file_path / final_filename
        return final_filename

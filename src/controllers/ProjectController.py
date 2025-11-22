from typing import Optional
from controllers.BaseController import BaseController
from pathlib import Path
import logging


class ProjectController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def get_project_path(self, project_id: str) -> Optional[Path]:
        data_file: Path = self.abs_asset_files_path / project_id
        try:
            data_file.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"get_project_path error occured {e}")
            return None
        return data_file

from controllers.BaseController import BaseController
from pathlib import Path


class ProjectController(BaseController):
    def __init__(self) -> None:
        super().__init__()

    def get_project_path(self, project_id: str) -> Path:
        data_file: Path = self.abs_asset_files_path / project_id
        try:
            data_file.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"An error occured{e}")
        return data_file

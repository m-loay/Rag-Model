from controllers.BaseController import BaseController
from pathlib import Path


class DBController(BaseController):
    def __init__(self) -> None:
        super().__init__()
        self.abs_db_path: Path = self.abs_asset_files_path / "database"

    def get_db_path(self, db_name: str) -> Path:
        db_path: Path = self.abs_db_path / db_name
        try:
            db_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"An error occured{e}")
        return db_path

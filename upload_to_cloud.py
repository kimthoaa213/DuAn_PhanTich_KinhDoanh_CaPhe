import site
import sys
from pathlib import Path


USER_SITE = site.getusersitepackages()
if Path(USER_SITE).exists() and USER_SITE not in sys.path:
    sys.path.insert(0, USER_SITE)

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.cloud_upload import upload_all_tables


if __name__ == "__main__":
    upload_all_tables(if_exists="replace", include_large_tables=False)

import site
import sys
from pathlib import Path


user_site = site.getusersitepackages()
if Path(user_site).exists() and user_site not in sys.path:
    sys.path.insert(0, user_site)

from src.pipeline import run_pipeline


if __name__ == "__main__":
    result = run_pipeline()
    print("Pipeline da chay xong.")
    print(f"File Excel ket qua: {result['output_excel']}")
    print("Cac bang clean nam trong: data/clean")
    print("Cac bang mart cho Tableau nam trong: data/mart")

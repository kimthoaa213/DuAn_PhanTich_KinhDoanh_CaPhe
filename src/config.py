from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]

# Tất cả đường dẫn được khai báo tương đối theo thư mục gốc dự án.
# Nhờ vậy khi gửi folder cho thành viên khác, code không phụ thuộc máy của riêng một người.
DATA_DIR = PROJECT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"
CLEAN_DIR = DATA_DIR / "clean"
MART_DIR = DATA_DIR / "mart"
MODEL_DATA_DIR = DATA_DIR / "model"

NOTEBOOK_DIR = PROJECT_DIR / "notebooks"
OUTPUT_DIR = PROJECT_DIR / "outputs"
EXCEL_OUTPUT_DIR = OUTPUT_DIR / "excel"
CHART_OUTPUT_DIR = OUTPUT_DIR / "charts"
MODEL_OUTPUT_DIR = OUTPUT_DIR / "models"

RAW_HIST_FILE = RAW_DIR / "Data_2023-2025.xlsx"
RAW_2026_FILE = RAW_DIR / "Data_Sales du an.xlsx"
RAW_COST_FILE = RAW_DIR / "Giá vốn theo sp.xlsx"

OUTPUT_EXCEL = EXCEL_OUTPUT_DIR / "Ket_qua_phan_tich_du_bao_pipeline.xlsx"


def ensure_directories() -> None:
    """Tạo sẵn các thư mục đầu ra để các bước pipeline có thể ghi file ổn định."""
    for path in [
        RAW_DIR,
        STAGING_DIR,
        CLEAN_DIR,
        MART_DIR,
        MODEL_DATA_DIR,
        NOTEBOOK_DIR,
        EXCEL_OUTPUT_DIR,
        CHART_OUTPUT_DIR,
        MODEL_OUTPUT_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def clear_directory(path: Path) -> None:
    """Xóa file output cũ trong thư mục sinh dữ liệu, không đụng vào data/raw."""
    path.mkdir(parents=True, exist_ok=True)
    for item in path.iterdir():
        if item.is_file():
            try:
                item.unlink()
            except PermissionError:
                # Trường hợp hay gặp: CSV đang mở trong Excel/Tableau nên Windows khóa file.
                # Khi đó bỏ qua file bị khóa để notebook không dừng toàn bộ quy trình.
                print(f"Bo qua file dang duoc mo/khoa: {item}")


def get_input_files() -> dict[str, Path]:
    """Kiểm tra đủ 3 file raw bắt buộc trước khi chạy làm sạch dữ liệu."""
    files = {
        "historical": RAW_HIST_FILE,
        "sales_2026": RAW_2026_FILE,
        "cost_2026": RAW_COST_FILE,
    }
    missing = {name: path for name, path in files.items() if not path.exists()}
    if missing:
        detail = ", ".join(f"{name}: {path}" for name, path in missing.items())
        raise FileNotFoundError(f"Thiếu file đầu vào trong data/raw: {detail}")
    return files

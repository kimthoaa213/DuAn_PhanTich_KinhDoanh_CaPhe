from pathlib import Path

import pandas as pd

from .utils import normalize_columns


def load_historical_excel(path: Path) -> pd.DataFrame:
    """Đọc toàn bộ sheet 2023-2025 và thêm cột nguồn sheet."""
    frames = []
    for sheet in pd.ExcelFile(path).sheet_names:
        # File lịch sử có thể tách theo nhiều sheet/năm, nên gom toàn bộ lại
        # và giữ tên sheet để truy vết nguồn dữ liệu khi cần kiểm tra.
        df = pd.read_excel(path, sheet_name=sheet)
        df = normalize_columns(df)
        df["Nguồn sheet"] = sheet
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def load_2026_excel(path: Path) -> pd.DataFrame:
    """Đọc dữ liệu bán hàng 2026."""
    # File 2026 đang dùng sheet cố định "data sales" theo cấu trúc raw hiện tại.
    df = pd.read_excel(path, sheet_name="data sales")
    return normalize_columns(df)


def load_cost_excel(path: Path) -> pd.DataFrame:
    """Đọc file giá vốn theo sản phẩm 2026."""
    # File giá vốn chỉ cần sheet đầu tiên; normalize_columns giúp tránh lỗi do tên cột dư khoảng trắng.
    sheet_name = pd.ExcelFile(path).sheet_names[0]
    df = pd.read_excel(path, sheet_name=sheet_name)
    return normalize_columns(df)

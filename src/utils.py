import re
import unicodedata
from pathlib import Path

import pandas as pd


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa tên cột: bỏ khoảng trắng đầu/cuối và gộp nhiều khoảng trắng."""
    df = df.copy()
    df.columns = [re.sub(r"\s+", " ", str(col).strip()) for col in df.columns]
    return df


def remove_vietnamese_accents(text) -> str:
    """Bỏ dấu tiếng Việt để tạo khóa so khớp dữ liệu ít nhạy với lỗi nhập liệu."""
    text = unicodedata.normalize("NFD", str(text))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def normalize_key(text) -> str:
    """Khóa so khớp không phân biệt dấu, hoa/thường và khoảng trắng."""
    if pd.isna(text):
        return ""
    text = re.sub(r"\s+", " ", str(text).strip())
    return remove_vietnamese_accents(text).lower()


def clean_text_series(series: pd.Series) -> pd.Series:
    """Chuẩn hóa cột text: bỏ khoảng trắng thừa và đưa chuỗi rỗng về null chuẩn."""
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA})
    )


def normalize_by_map(series: pd.Series, mapping: dict) -> pd.Series:
    """Map giá trị lộn xộn về giá trị chuẩn, không phân biệt dấu/hoa thường/khoảng trắng."""
    normalized_mapping = {normalize_key(key): value for key, value in mapping.items()}
    series = clean_text_series(series)
    return series.map(
        lambda value: normalized_mapping.get(normalize_key(value), value)
        if pd.notna(value)
        else value
    )


def to_number(series: pd.Series) -> pd.Series:
    """Chuyển numeric, fill null = 0 theo logic dữ liệu hóa đơn."""
    return pd.to_numeric(series, errors="coerce").fillna(0)


def ensure_columns(df: pd.DataFrame, columns: list[str], default=pd.NA) -> pd.DataFrame:
    """Bảo đảm schema có đủ cột cần dùng, kể cả khi file nguồn thiếu một vài cột."""
    df = df.copy()
    for col in columns:
        if col not in df.columns:
            df[col] = default
    return df


def write_table(df: pd.DataFrame, path_without_suffix: Path) -> None:
    """Xuất CSV cho Tableau và notebook."""
    path_without_suffix.parent.mkdir(parents=True, exist_ok=True)
    output_path = path_without_suffix.with_suffix(".csv")
    try:
        # utf-8-sig giúp Excel trên Windows mở tiếng Việt ít bị lỗi font hơn.
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
    except PermissionError:
        print(f"Khong ghi duoc vi file dang mo/khoa: {output_path}")


def data_overview(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """Tạo bảng kiểm tra nhanh chất lượng dữ liệu cho mỗi giai đoạn xử lý."""
    # Không tính cột audit "Cờ duplicate" khi kiểm tra trùng toàn dòng.
    # Nếu tính cả cột này, dòng đầu tiên của một nhóm trùng là False còn dòng sau là True,
    # khiến duplicated() cho kết quả thấp giả tạo sau bước clean.
    duplicate_check = df.drop(columns=["Cờ duplicate"], errors="ignore")
    duplicate_flag_count = (
        int(df["Cờ duplicate"].fillna(False).astype(bool).sum())
        if "Cờ duplicate" in df.columns
        else pd.NA
    )
    return pd.DataFrame(
        {
            "Bảng": [table_name],
            "Số dòng": [len(df)],
            "Số cột": [df.shape[1]],
            "Số ô null": [int(df.isna().sum().sum())],
            "Số dòng duplicate toàn dòng": [int(duplicate_check.duplicated().sum())],
            "Số dòng duplicate theo cờ": [duplicate_flag_count],
        }
    )

from pathlib import Path
import hashlib

import pandas as pd

from .config import CLEAN_DIR, MART_DIR, RAW_COST_FILE, RAW_DIR, ensure_directories
from .extract import load_cost_excel
from .mart import build_all_marts
from .pipeline import load_final_sales
from .transform import add_analysis_columns, clean_cost, clean_sales_2026
from .utils import clean_text_series, normalize_columns, write_table


DEFAULT_NEW_ORDERS_FILE = RAW_DIR / "new_orders.csv"
PENDING_CLOUD_FILE = CLEAN_DIR / "pending_cloud_sales_final.csv"
INTERNAL_LINE_KEY = "_line_key"
LEGACY_KEY_COLUMNS = ["line_key", "transaction_line_key"]

# Kiem trung theo cap do dong giao dich, khong chi theo So chung tu.
# Nhu vay mot hoa don co nhieu dong san pham van duoc giu rieng.
LINE_DUPLICATE_COLUMNS = [
    "Ngay chung tu",
    "So chung tu",
    "DVT",
    "So luong",
    "Khoi luong KG",
    "Don gia",
    "Doanh so",
    "Chiet khau",
    "Doanh thu thuan",
    "So luong tra lai",
    "Gia tri tra lai",
    "Ma khach hang",
    "Ten khach hang",
    "Nhom khach hang",
    "Ma san pham",
    "Ten san pham",
    "Nhom san pham",
    "Loai san pham",
    "Kenh",
    "Chi nhanh",
    "Vung doanh thu",
    "Tra hang",
]

NUMERIC_DUPLICATE_COLUMNS = {
    "So luong",
    "Khoi luong KG",
    "Don gia",
    "Doanh so",
    "Chiet khau",
    "Doanh thu thuan",
    "So luong tra lai",
    "Gia tri tra lai",
}

FINAL_COLUMNS_2026 = {
    "Ngay chung tu": "Ngày chứng từ",
    "Nam": "Năm",
    "Thang": "Tháng",
    "Quy": "Quý",
    "Nam-Thang": "Năm-Tháng",
    "So chung tu": "Số chứng từ",
    "DVT": "ĐVT",
    "So luong": "Số lượng",
    "Khoi luong KG": "Khối lượng KG",
    "Don gia": "Đơn giá",
    "Doanh so": "Doanh số",
    "Chiet khau": "Chiết khấu",
    "Doanh thu thuan": "Doanh thu thuần",
    "So luong tra lai": "Số lượng trả lại",
    "Gia tri tra lai": "Giá trị trả lại",
    "Gia von don vi": "Giá vốn đơn vị",
    "Tong gia von": "Tổng giá vốn",
    "Loi nhuan": "Lợi nhuận",
    "Loi nhuan tinh lai": "Lợi nhuận tính lại",
    "Ma khach hang": "Mã khách hàng",
    "Ten khach hang": "Tên khách hàng",
    "Nhom khach hang": "Nhóm khách hàng",
    "Ma san pham": "Mã sản phẩm",
    "Ten san pham": "Tên sản phẩm",
    "Nhom san pham": "Nhóm sản phẩm",
    "Loai san pham": "Loại sản phẩm",
    "Kenh": "Kênh",
    "Chi nhanh": "Chi nhánh",
    "Vung doanh thu": "Vùng doanh thu",
    "Tra hang": "Trả hàng",
    "Giai doan": "Giai đoạn",
    "Nguon du lieu": "Nguồn dữ liệu",
    "Co du lieu gia von": "Có dữ liệu giá vốn",
    "Co duplicate": "Cờ duplicate",
}


def load_new_orders(path: Path) -> pd.DataFrame:
    """Doc file hoa don moi co cau truc giong sheet data sales nam 2026."""
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file hoa don moi: {path}")

    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path, low_memory=False)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path, sheet_name="data sales")
    else:
        raise ValueError("File hoa don moi chi ho tro .csv, .xlsx hoac .xls")
    return normalize_columns(df)


def build_new_orders_final(new_orders_clean: pd.DataFrame) -> pd.DataFrame:
    """Dua du lieu moi da clean ve dung schema cua sales_final.csv."""
    final = pd.DataFrame(
        {
            "Ngày chứng từ": new_orders_clean["Ngày chứng từ"],
            "Năm": new_orders_clean["Năm"],
            "Tháng": new_orders_clean["Tháng"],
            "Quý": new_orders_clean["Quý"],
            "Năm-Tháng": new_orders_clean["Năm-Tháng"],
            "Số chứng từ": new_orders_clean["Số chứng từ"],
            "ĐVT": new_orders_clean["ĐVT"],
            "Số lượng": new_orders_clean["Tổng số lượng bán"],
            "Khối lượng KG": new_orders_clean["Khối lượng"],
            "Đơn giá": new_orders_clean["Đơn Giá Chuẩn"],
            "Doanh số": new_orders_clean["Doanh số bán"],
            "Chiết khấu": new_orders_clean["Chiết khấu"],
            "Doanh thu thuần": new_orders_clean["Doanh thu thuần"],
            "Số lượng trả lại": new_orders_clean["Tổng số lượng trả lại"],
            "Giá trị trả lại": new_orders_clean["Giá trị trả lại"],
            "Giá vốn đơn vị": new_orders_clean["Giá vốn đơn vị"],
            "Tổng giá vốn": new_orders_clean["Tổng giá vốn"],
            "Lợi nhuận": new_orders_clean["Lợi nhuận"],
            "Lợi nhuận tính lại": new_orders_clean["Lợi nhuận tính lại"],
            "Mã khách hàng": new_orders_clean["Mã khách hàng2"],
            "Tên khách hàng": new_orders_clean["Tên khách hàng2"],
            "Nhóm khách hàng": new_orders_clean["Nhóm khách hàng"],
            "Mã sản phẩm": new_orders_clean["Mã sản phẩm"],
            "Tên sản phẩm": new_orders_clean["Tên sản phẩm"].fillna(new_orders_clean["Tên sản phẩm chuẩn"]),
            "Nhóm sản phẩm": new_orders_clean["Nhóm sản phẩm"].fillna(new_orders_clean["Nhóm sản phẩm chuẩn"]),
            "Loại sản phẩm": new_orders_clean["Loại sản phẩm"].fillna(new_orders_clean["Loại sản phẩm chuẩn"]),
            "Kênh": new_orders_clean["Kênh"],
            "Chi nhánh": new_orders_clean["Chi nhánh"],
            "Vùng doanh thu": new_orders_clean["Vùng doanh thu"],
            "Trả hàng": new_orders_clean["Trả hàng"],
            "Giai đoạn": new_orders_clean["Giai đoạn"],
            "Nguồn dữ liệu": "2026_incremental",
            "Có dữ liệu giá vốn": new_orders_clean["Có dữ liệu giá vốn"],
            "Cờ duplicate": new_orders_clean["Cờ duplicate"],
        }
    )
    return add_analysis_columns(final)


def _duplicate_columns(existing_sales: pd.DataFrame, new_sales: pd.DataFrame) -> list[str]:
    columns = [FINAL_COLUMNS_2026[col] for col in LINE_DUPLICATE_COLUMNS]
    return [col for col in columns if col in existing_sales.columns and col in new_sales.columns]


def _row_signature(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    signed = df[columns].copy()
    numeric_columns = {FINAL_COLUMNS_2026[col] for col in NUMERIC_DUPLICATE_COLUMNS}
    date_columns = {FINAL_COLUMNS_2026["Ngay chung tu"]}
    for col in columns:
        if col in date_columns:
            signed[col] = pd.to_datetime(signed[col], errors="coerce").dt.strftime("%Y-%m-%d")
        elif col in numeric_columns:
            numeric = pd.to_numeric(signed[col], errors="coerce").round(4)
            signed[col] = numeric.map(lambda value: "<NULL>" if pd.isna(value) else f"{value:.4f}")
        else:
            signed[col] = clean_text_series(signed[col]).astype("string").str.casefold()
    signed = signed.fillna("<NULL>")
    return signed.apply(
        lambda row: hashlib.blake2b("|".join(row.astype(str)).encode("utf-8"), digest_size=8).hexdigest(),
        axis=1,
    )


def _drop_key_columns(df: pd.DataFrame) -> pd.DataFrame:
    key_columns = [INTERNAL_LINE_KEY, *LEGACY_KEY_COLUMNS]
    return df.drop(columns=[col for col in key_columns if col in df.columns], errors="ignore")


def add_internal_line_key(df: pd.DataFrame) -> pd.DataFrame:
    """Tao khoa noi bo de kiem trung, khong ghi vao bang du lieu chinh."""
    result = df.copy()
    columns = [FINAL_COLUMNS_2026[col] for col in LINE_DUPLICATE_COLUMNS if FINAL_COLUMNS_2026[col] in result.columns]
    if not columns:
        raise ValueError("Khong co cot de tao khoa kiem trung dong giao dich.")
    result[INTERNAL_LINE_KEY] = _row_signature(result, columns)
    return result


def filter_new_lines(existing_sales: pd.DataFrame, new_sales: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Bo cac dong trung ca dong giao dich voi du lieu da co hoac trung lap trong file moi."""
    existing_sales = add_internal_line_key(_drop_key_columns(existing_sales))
    new_sales = add_internal_line_key(_drop_key_columns(new_sales))
    source_columns = _duplicate_columns(existing_sales, new_sales)
    columns = [INTERNAL_LINE_KEY]
    if not columns:
        raise ValueError("Khong co cot chung de kiem tra trung dong giao dich.")

    existing_signatures = set(existing_sales[INTERNAL_LINE_KEY].astype("string"))
    new_signatures = new_sales[INTERNAL_LINE_KEY].astype("string")
    duplicate_existing = new_signatures.isin(existing_signatures)
    duplicate_inside_file = new_signatures.duplicated(keep="first")
    keep_mask = ~(duplicate_existing | duplicate_inside_file)

    return _drop_key_columns(new_sales.loc[keep_mask].copy()), {
        "raw_new_rows": int(len(new_sales)),
        "duplicate_with_existing_rows": int(duplicate_existing.sum()),
        "duplicate_inside_new_file_rows": int(duplicate_inside_file.sum()),
        "appended_rows": int(keep_mask.sum()),
        "duplicate_check_columns": source_columns,
        "duplicate_key_column": "internal_only",
    }


def load_pending_cloud_rows(columns: list[str] | None = None) -> pd.DataFrame:
    """Doc cac dong da append local nhung chua dong bo cloud."""
    if not PENDING_CLOUD_FILE.exists():
        return pd.DataFrame(columns=columns)
    pending = pd.read_csv(PENDING_CLOUD_FILE, low_memory=False)
    pending = _drop_key_columns(pending)
    if columns is not None:
        pending = pending.reindex(columns=columns)
    return pending


def save_pending_cloud_rows(rows: pd.DataFrame) -> None:
    """Luu cac dong cho upload cloud sau; neu rong thi lam rong file."""
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    rows = _drop_key_columns(rows.copy())
    rows.to_csv(PENDING_CLOUD_FILE, index=False, encoding="utf-8-sig")


def append_pending_cloud_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """Gom pending cu voi dong moi va loai trung trong pending."""
    rows = _drop_key_columns(rows.copy())
    pending = load_pending_cloud_rows(rows.columns.tolist())
    if pending.empty:
        combined = rows.copy()
    elif rows.empty:
        combined = pending.copy()
    else:
        combined = pd.concat([pending, rows], ignore_index=True)
    if combined.empty:
        save_pending_cloud_rows(combined)
        return combined
    signed = add_internal_line_key(combined)
    combined = _drop_key_columns(signed.loc[~signed[INTERNAL_LINE_KEY].duplicated(keep="first")])
    save_pending_cloud_rows(combined)
    return combined


def clear_pending_cloud_rows(columns: list[str] | None = None) -> None:
    """Lam rong hang doi upload cloud nhung van giu file de de kiem tra."""
    save_pending_cloud_rows(pd.DataFrame(columns=columns))


def rebuild_local_marts(updated_sales: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Tinh lai toan bo fact/dim/mart tu sales_final da cap nhat."""
    marts = build_all_marts(updated_sales)
    for name, df in marts.items():
        write_table(df, MART_DIR / name)
    return marts


def run_incremental_update(
    new_orders_path: Path | str = DEFAULT_NEW_ORDERS_FILE,
    upload_cloud: bool = False,
) -> dict:
    """Chay luong mo rong: clean hoa don moi, append local, rebuild mart va tuy chon upload cloud."""
    ensure_directories()
    new_orders_path = Path(new_orders_path)

    loaded_sales = load_final_sales()
    should_rewrite_existing_sales = any(col in loaded_sales.columns for col in LEGACY_KEY_COLUMNS)
    existing_sales_raw = _drop_key_columns(loaded_sales)
    sales_before_update = existing_sales_raw.copy()
    raw_new_orders = load_new_orders(new_orders_path)
    cost_clean = clean_cost(load_cost_excel(RAW_COST_FILE))
    new_orders_clean = clean_sales_2026(raw_new_orders, cost_clean)
    existing_sales = existing_sales_raw
    if should_rewrite_existing_sales:
        write_table(existing_sales, CLEAN_DIR / "sales_final")
        rebuild_local_marts(existing_sales)
    new_sales = _drop_key_columns(build_new_orders_final(new_orders_clean))
    new_sales = new_sales.reindex(columns=existing_sales.columns)

    rows_to_append, report = filter_new_lines(existing_sales, new_sales)
    if not rows_to_append.empty:
        pending_rows = append_pending_cloud_rows(rows_to_append)
    else:
        pending_rows = load_pending_cloud_rows(existing_sales.columns.tolist())

    if rows_to_append.empty:
        result = {
            "sales_before_update": sales_before_update,
            "updated_sales": existing_sales,
            "new_orders_clean": new_orders_clean,
            "rows_to_append": rows_to_append,
            "marts": {},
            "report": report,
            "pending_rows": pending_rows,
            "uploaded_cloud": False,
        }
        if upload_cloud:
            upload_pending_cloud(result)
        return result

    updated_sales = pd.concat([existing_sales, rows_to_append], ignore_index=True)
    updated_sales = add_analysis_columns(updated_sales)
    write_table(updated_sales, CLEAN_DIR / "sales_final")

    marts = rebuild_local_marts(updated_sales)

    result = {
        "sales_before_update": sales_before_update,
        "updated_sales": updated_sales,
        "new_orders_clean": new_orders_clean,
        "rows_to_append": rows_to_append,
        "marts": marts,
        "report": report,
        "pending_rows": pending_rows,
        "uploaded_cloud": False,
    }
    if upload_cloud:
        upload_pending_cloud(result)
    return result


def upload_pending_cloud(result: dict) -> bool:
    """Upload cac dong pending sau khi da in xong summary local."""
    pending_rows = result.get("pending_rows")
    if pending_rows is None or pending_rows.empty:
        return False

    from .cloud_upload import upload_incremental_cloud

    upload_incremental_cloud(pending_rows)
    updated_sales = result.get("updated_sales")
    columns = updated_sales.columns.tolist() if updated_sales is not None else None
    clear_pending_cloud_rows(columns)
    result["uploaded_cloud"] = True
    return True

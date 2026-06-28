import numpy as np
import pandas as pd

from .utils import clean_text_series, ensure_columns, normalize_by_map, to_number


MAP_CHANNEL = {
    "khac": "Khác",
    "xuat khau": "Xuất khẩu",
    "quan noi bo": "Quán nội bộ",
    "online": "Online",
    "mt": "MT",
    "gt": "GT",
    "horeca": "HORECA",
    "oem": "OEM",
}

# Các bảng map dùng để gom nhiều cách nhập liệu về cùng một giá trị chuẩn.
# Ví dụ "khac", "Khác", "KHÁC" đều được chuẩn hóa về "Khác" qua normalize_by_map().
MAP_PRODUCT_GROUP = {
    "hoa tan": "Hòa tan",
    "hoa tan ": "Hòa tan",
    "hòa tan": "Hòa tan",
    "rang xay": "Rang xay",
    "do uong": "Đồ uống",
    "khac": "Khác",
}

MAP_CUSTOMER_GROUP = {
    "nhom khach hang noi dia": "Nhóm khách hàng nội địa",
    "nhom khach hang noi dia ": "Nhóm khách hàng nội địa",
    "nhóm khách hàng nội đia": "Nhóm khách hàng nội địa",
    "nhóm khách hàng nội địa": "Nhóm khách hàng nội địa",
    "internal": "Internal",
    "online": "Online",
    "f&b": "F&B",
    "distributor": "Distributor",
    "corporate": "Corporate",
    "airport": "Airport",
    "retail": "Retail",
    "export": "Export",
    "oem": "OEM",
}

MAP_RETURN = {
    "no": "Không",
    "khong": "Không",
    "không": "Không",
    "yes": "Có",
    "co": "Có",
    "có": "Có",
}


HIST_REQUIRED_COLUMNS = [
    "Ngày chứng từ",
    "Số chứng từ",
    "ĐVT",
    "Quy đổi",
    "Số lượng (KG )",
    "Số lượng",
    "Giá bán",
    "Doanh số",
    "Chiết khấu",
    "Doanh thu thuần",
    "Tên nhóm KH1",
    "Tháng",
    "Mã khách hàng",
    "Mã sản phẩm",
    "Kênh",
    "Nhóm sp",
    "Trả hàng",
    "Lợi nhuận",
    "Nguồn sheet",
]

SALES_2026_REQUIRED_COLUMNS = [
    "Ngày chứng từ",
    "Số chứng từ",
    "ĐVT",
    "Tổng số lượng bán",
    "Đơn Giá Chuẩn",
    "Doanh số bán",
    "Chiết khấu",
    "Doanh thu thuần",
    "Tổng số lượng trả lại",
    "Giá trị trả lại",
    "Kênh",
    "Tỷ lệ chuyển đổi",
    "Chi nhánh",
    "Vùng doanh thu",
    "Khối lượng",
    "Mã sản phẩm",
    "Tên sản phẩm",
    "Nhóm sản phẩm",
    "Loại sản phẩm",
    "Mã khách hàng2",
    "Tên khách hàng2",
    "Nhóm khách hàng",
]

COST_REQUIRED_COLUMNS = [
    "Mã Sản phẩm",
    "Nhóm SP Chuẩn",
    "Loại SP Chuẩn",
    "Tên SP Mới",
    "Giá bán lẻ",
    "Giá vốn",
]


def add_date_columns(df: pd.DataFrame, date_col: str = "Ngày chứng từ") -> pd.DataFrame:
    """Tạo các cột thời gian dùng chung cho EDA, mart và mô hình dự báo."""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df["Năm"] = df[date_col].dt.year
    df["Tháng"] = df[date_col].dt.month
    df["Quý"] = df[date_col].dt.quarter
    df["Năm-Tháng"] = df[date_col].dt.strftime("%Y-%m")
    return df


def clean_historical(df: pd.DataFrame) -> pd.DataFrame:
    """Làm sạch dữ liệu bán hàng 2023-2025."""
    # Bước 1: ép dữ liệu về đúng bộ cột cần phân tích.
    # ensure_columns giúp pipeline không vỡ nếu file thiếu cột phụ, nhưng vẫn giữ schema thống nhất.
    df = ensure_columns(df, HIST_REQUIRED_COLUMNS)
    df = df[HIST_REQUIRED_COLUMNS].copy()

    numeric_cols = [
        "Quy đổi",
        "Số lượng (KG )",
        "Số lượng",
        "Giá bán",
        "Doanh số",
        "Chiết khấu",
        "Doanh thu thuần",
        "Tháng",
        "Lợi nhuận",
    ]
    text_cols = [
        "Số chứng từ",
        "ĐVT",
        "Tên nhóm KH1",
        "Mã khách hàng",
        "Mã sản phẩm",
        "Kênh",
        "Nhóm sp",
        "Trả hàng",
        "Nguồn sheet",
    ]

    df["Ngày chứng từ"] = pd.to_datetime(df["Ngày chứng từ"], errors="coerce")
    for col in numeric_cols:
        # Với dữ liệu hóa đơn, null ở cột số được xem như 0 để không làm sai tổng tiền/số lượng.
        df[col] = to_number(df[col])
    for col in text_cols:
        df[col] = clean_text_series(df[col])

    # Chuẩn hóa giá trị phân loại để khi groupby không bị tách thành nhiều nhóm do sai hoa/thường/chính tả.
    df["Kênh"] = normalize_by_map(df["Kênh"], MAP_CHANNEL)
    df["Nhóm sp"] = normalize_by_map(df["Nhóm sp"], MAP_PRODUCT_GROUP)
    df["Tên nhóm KH1"] = normalize_by_map(df["Tên nhóm KH1"], MAP_CUSTOMER_GROUP)
    df["Trả hàng"] = normalize_by_map(df["Trả hàng"], MAP_RETURN)
    df = add_date_columns(df)

    df["Giai đoạn"] = "Trước tái cấu trúc"
    df["Nguồn dữ liệu"] = "2023-2025"
    # Giai đoạn 2023-2025 đã có lợi nhuận nhưng chưa có file giá vốn chi tiết,
    # nên để trống giá vốn ở bước clean và suy ra sau khi merge thành final.
    df["Giá vốn đơn vị"] = np.nan
    df["Tổng giá vốn"] = np.nan
    df["Lợi nhuận tính lại"] = df["Lợi nhuận"]
    df["Có dữ liệu giá vốn"] = False
    # Chỉ gắn cờ duplicate để người phân tích nhìn thấy vấn đề; không xóa vì dữ liệu hóa đơn
    # có thể có nhiều dòng hợp lệ trên cùng chứng từ/sản phẩm.
    df["Cờ duplicate"] = df.duplicated()
    return df


def clean_cost(df: pd.DataFrame) -> pd.DataFrame:
    """Làm sạch bảng giá vốn sản phẩm 2026."""
    df = ensure_columns(df, COST_REQUIRED_COLUMNS)
    df = df[COST_REQUIRED_COLUMNS].copy()
    for col in ["Mã Sản phẩm", "Nhóm SP Chuẩn", "Loại SP Chuẩn", "Tên SP Mới"]:
        df[col] = clean_text_series(df[col])
    for col in ["Giá bán lẻ", "Giá vốn"]:
        df[col] = to_number(df[col])

    df["Nhóm SP Chuẩn"] = normalize_by_map(df["Nhóm SP Chuẩn"], MAP_PRODUCT_GROUP)
    # Nếu một mã sản phẩm xuất hiện nhiều lần trong file giá vốn, giữ bản ghi cuối cùng
    # như giá vốn cập nhật gần nhất để merge vào dữ liệu bán hàng 2026.
    df = df.drop_duplicates(subset=["Mã Sản phẩm"], keep="last")
    return df


def clean_sales_2026(df: pd.DataFrame, cost: pd.DataFrame) -> pd.DataFrame:
    """Làm sạch 2026, merge giá vốn theo sản phẩm và tính lợi nhuận."""
    # File 2026 có cấu trúc khác 2023-2025, nên trước tiên chuẩn hóa riêng
    # rồi mới đưa về schema chung trong build_final_sales().
    df = ensure_columns(df, SALES_2026_REQUIRED_COLUMNS)
    df = df[SALES_2026_REQUIRED_COLUMNS].copy()

    numeric_cols = [
        "Tổng số lượng bán",
        "Đơn Giá Chuẩn",
        "Doanh số bán",
        "Chiết khấu",
        "Doanh thu thuần",
        "Tổng số lượng trả lại",
        "Giá trị trả lại",
        "Tỷ lệ chuyển đổi",
        "Khối lượng",
    ]
    text_cols = [
        "Số chứng từ",
        "ĐVT",
        "Kênh",
        "Chi nhánh",
        "Vùng doanh thu",
        "Mã sản phẩm",
        "Tên sản phẩm",
        "Nhóm sản phẩm",
        "Loại sản phẩm",
        "Mã khách hàng2",
        "Tên khách hàng2",
        "Nhóm khách hàng",
    ]

    df["Ngày chứng từ"] = pd.to_datetime(df["Ngày chứng từ"], errors="coerce")
    for col in numeric_cols:
        df[col] = to_number(df[col])
    for col in text_cols:
        df[col] = clean_text_series(df[col])

    df["Kênh"] = normalize_by_map(df["Kênh"], MAP_CHANNEL)
    df["Nhóm sản phẩm"] = normalize_by_map(df["Nhóm sản phẩm"], MAP_PRODUCT_GROUP)
    df["Nhóm khách hàng"] = normalize_by_map(df["Nhóm khách hàng"], MAP_CUSTOMER_GROUP)
    df = add_date_columns(df)

    cost_merge = cost.rename(
        columns={
            "Mã Sản phẩm": "Mã sản phẩm",
            "Nhóm SP Chuẩn": "Nhóm sản phẩm chuẩn",
            "Loại SP Chuẩn": "Loại sản phẩm chuẩn",
            "Tên SP Mới": "Tên sản phẩm chuẩn",
            "Giá vốn": "Giá vốn đơn vị",
        }
    )
    # Merge left để giữ toàn bộ dòng bán hàng 2026, kể cả sản phẩm chưa có giá vốn.
    # Các dòng không match giá vốn sẽ được cờ "Có dữ liệu giá vốn" = False.
    df = df.merge(
        cost_merge[
            [
                "Mã sản phẩm",
                "Nhóm sản phẩm chuẩn",
                "Loại sản phẩm chuẩn",
                "Tên sản phẩm chuẩn",
                "Giá bán lẻ",
                "Giá vốn đơn vị",
            ]
        ],
        on="Mã sản phẩm",
        how="left",
    )
    df["Giá vốn đơn vị"] = to_number(df["Giá vốn đơn vị"])
    # Lợi nhuận 2026 được tính lại từ doanh thu thuần và giá vốn sau khi merge.
    df["Tổng giá vốn"] = df["Giá vốn đơn vị"] * df["Tổng số lượng bán"]
    df["Lợi nhuận tính lại"] = df["Doanh thu thuần"] - df["Tổng giá vốn"]
    df["Lợi nhuận"] = df["Lợi nhuận tính lại"]
    df["Có dữ liệu giá vốn"] = df["Giá vốn đơn vị"] > 0
    df["Trả hàng"] = np.where(df["Giá trị trả lại"] > 0, "Có", "Không")
    df["Giai đoạn"] = "Sau tái cấu trúc"
    df["Nguồn dữ liệu"] = "2026"
    # Duplicate chỉ được hiển thị để kiểm tra chất lượng dữ liệu, không tự động xóa.
    df["Cờ duplicate"] = df.duplicated()
    return df


def build_final_sales(hist: pd.DataFrame, sales_2026: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa schema và gộp 2023-2026 thành data final."""
    # hist_final và current_final là bước "đổi tên/đưa về cùng nghĩa".
    # Sau bước này Tableau/notebook chỉ cần làm việc với một bộ cột thống nhất.
    hist_final = pd.DataFrame(
        {
            "Ngày chứng từ": hist["Ngày chứng từ"],
            "Năm": hist["Năm"],
            "Tháng": hist["Tháng"],
            "Quý": hist["Quý"],
            "Năm-Tháng": hist["Năm-Tháng"],
            "Số chứng từ": hist["Số chứng từ"],
            "ĐVT": hist["ĐVT"],
            "Số lượng": hist["Số lượng"],
            "Khối lượng KG": hist["Số lượng (KG )"],
            "Đơn giá": hist["Giá bán"],
            "Doanh số": hist["Doanh số"],
            "Chiết khấu": hist["Chiết khấu"],
            "Doanh thu thuần": hist["Doanh thu thuần"],
            "Số lượng trả lại": 0.0,
            "Giá trị trả lại": 0.0,
            "Giá vốn đơn vị": hist["Giá vốn đơn vị"],
            "Tổng giá vốn": hist["Tổng giá vốn"],
            "Lợi nhuận": hist["Lợi nhuận"],
            "Lợi nhuận tính lại": hist["Lợi nhuận tính lại"],
            "Mã khách hàng": hist["Mã khách hàng"],
            "Tên khách hàng": pd.NA,
            "Nhóm khách hàng": hist["Tên nhóm KH1"],
            "Mã sản phẩm": hist["Mã sản phẩm"],
            "Tên sản phẩm": pd.NA,
            "Nhóm sản phẩm": hist["Nhóm sp"],
            "Loại sản phẩm": pd.NA,
            "Kênh": hist["Kênh"],
            "Chi nhánh": pd.NA,
            "Vùng doanh thu": pd.NA,
            "Trả hàng": hist["Trả hàng"],
            "Giai đoạn": hist["Giai đoạn"],
            "Nguồn dữ liệu": hist["Nguồn dữ liệu"],
            "Có dữ liệu giá vốn": hist["Có dữ liệu giá vốn"],
            "Cờ duplicate": hist["Cờ duplicate"],
        }
    )

    current_final = pd.DataFrame(
        {
            "Ngày chứng từ": sales_2026["Ngày chứng từ"],
            "Năm": sales_2026["Năm"],
            "Tháng": sales_2026["Tháng"],
            "Quý": sales_2026["Quý"],
            "Năm-Tháng": sales_2026["Năm-Tháng"],
            "Số chứng từ": sales_2026["Số chứng từ"],
            "ĐVT": sales_2026["ĐVT"],
            "Số lượng": sales_2026["Tổng số lượng bán"],
            "Khối lượng KG": sales_2026["Khối lượng"],
            "Đơn giá": sales_2026["Đơn Giá Chuẩn"],
            "Doanh số": sales_2026["Doanh số bán"],
            "Chiết khấu": sales_2026["Chiết khấu"],
            "Doanh thu thuần": sales_2026["Doanh thu thuần"],
            "Số lượng trả lại": sales_2026["Tổng số lượng trả lại"],
            "Giá trị trả lại": sales_2026["Giá trị trả lại"],
            "Giá vốn đơn vị": sales_2026["Giá vốn đơn vị"],
            "Tổng giá vốn": sales_2026["Tổng giá vốn"],
            "Lợi nhuận": sales_2026["Lợi nhuận"],
            "Lợi nhuận tính lại": sales_2026["Lợi nhuận tính lại"],
            "Mã khách hàng": sales_2026["Mã khách hàng2"],
            "Tên khách hàng": sales_2026["Tên khách hàng2"],
            "Nhóm khách hàng": sales_2026["Nhóm khách hàng"],
            "Mã sản phẩm": sales_2026["Mã sản phẩm"],
            "Tên sản phẩm": sales_2026["Tên sản phẩm"].fillna(sales_2026["Tên sản phẩm chuẩn"]),
            "Nhóm sản phẩm": sales_2026["Nhóm sản phẩm"].fillna(sales_2026["Nhóm sản phẩm chuẩn"]),
            "Loại sản phẩm": sales_2026["Loại sản phẩm"].fillna(sales_2026["Loại sản phẩm chuẩn"]),
            "Kênh": sales_2026["Kênh"],
            "Chi nhánh": sales_2026["Chi nhánh"],
            "Vùng doanh thu": sales_2026["Vùng doanh thu"],
            "Trả hàng": sales_2026["Trả hàng"],
            "Giai đoạn": sales_2026["Giai đoạn"],
            "Nguồn dữ liệu": sales_2026["Nguồn dữ liệu"],
            "Có dữ liệu giá vốn": sales_2026["Có dữ liệu giá vốn"],
            "Cờ duplicate": sales_2026["Cờ duplicate"],
        }
    )

    final_columns = hist_final.columns.tolist()
    # Tránh FutureWarning của pandas khi concat các cột toàn null, sau đó reindex để vẫn giữ đủ schema.
    hist_for_concat = hist_final.dropna(axis=1, how="all")
    current_for_concat = current_final.dropna(axis=1, how="all")
    final = pd.concat([hist_for_concat, current_for_concat], ignore_index=True)
    final = final.reindex(columns=final_columns)
    final = add_analysis_columns(final)
    return final


def add_analysis_columns(final: pd.DataFrame) -> pd.DataFrame:
    """Tạo các cột chỉ số sau khi đã merge toàn bộ dữ liệu 2023-2026."""
    final = final.copy()

    # Chuẩn hóa lại text sau khi concat để tránh các biến thể nhìn giống nhau
    # như "2026" và "2026 " làm sai filter/groupby ở các bước sau.
    text_cols = [
        "Số chứng từ",
        "ĐVT",
        "Mã khách hàng",
        "Tên khách hàng",
        "Nhóm khách hàng",
        "Mã sản phẩm",
        "Tên sản phẩm",
        "Nhóm sản phẩm",
        "Loại sản phẩm",
        "Kênh",
        "Chi nhánh",
        "Vùng doanh thu",
        "Trả hàng",
        "Giai đoạn",
        "Nguồn dữ liệu",
    ]
    for col in text_cols:
        if col in final.columns:
            final[col] = clean_text_series(final[col])

    # Sau khi merge 2023-2025 và 2026, một số cột mô tả chỉ tồn tại ở một nguồn dữ liệu.
    # Ví dụ 2023-2025 không có Chi nhánh/Vùng doanh thu/Tên sản phẩm chi tiết.
    # Các null này là hợp lý về nghiệp vụ, nhưng thay bằng nhãn rõ nghĩa để Tableau dễ đọc hơn.
    text_fill_values = {
        "Số chứng từ": "Không xác định",
        "ĐVT": "Không xác định",
        "Mã khách hàng": "Không xác định",
        "Tên khách hàng": "Không có dữ liệu",
        "Nhóm khách hàng": "Không xác định",
        "Mã sản phẩm": "Không xác định",
        "Tên sản phẩm": "Không có dữ liệu",
        "Nhóm sản phẩm": "Không xác định",
        "Loại sản phẩm": "Không có dữ liệu",
        "Kênh": "Không xác định",
        "Chi nhánh": "Không áp dụng",
        "Vùng doanh thu": "Không áp dụng",
        "Trả hàng": "Không",
        "Giai đoạn": "Không xác định",
        "Nguồn dữ liệu": "Không xác định",
    }
    for col, fill_value in text_fill_values.items():
        if col in final.columns:
            final[col] = final[col].fillna(fill_value)

    if "Có dữ liệu giá vốn" in final.columns:
        final["Có dữ liệu giá vốn"] = final["Có dữ liệu giá vốn"].fillna(False)
    if "Cờ duplicate" in final.columns:
        final["Cờ duplicate"] = final["Cờ duplicate"].fillna(False)

    # 2023-2025 không có file giá vốn chi tiết, nhưng có lợi nhuận.
    # Vì vậy suy ra tổng giá vốn để bảng final có cùng hệ chỉ tiêu với 2026.
    missing_cost = final["Tổng giá vốn"].isna()
    final.loc[missing_cost, "Tổng giá vốn"] = (
        final.loc[missing_cost, "Doanh thu thuần"] - final.loc[missing_cost, "Lợi nhuận"]
    )

    final["Giá vốn đơn vị"] = np.where(
        (final["Giá vốn đơn vị"].isna()) & (final["Số lượng"] != 0),
        final["Tổng giá vốn"] / final["Số lượng"].replace(0, np.nan),
        final["Giá vốn đơn vị"],
    )

    # Cột lợi nhuận tính lại giúp kiểm tra nhất quán giữa doanh thu, giá vốn và lợi nhuận gốc.
    final["Lợi nhuận tính lại"] = np.where(
        final["Tổng giá vốn"].notna(),
        final["Doanh thu thuần"] - final["Tổng giá vốn"],
        final["Lợi nhuận"],
    )

    # Các tỷ lệ được tạo sau khi đã có final để cả 2023-2025 và 2026 đều có cùng hệ chỉ tiêu.
    final["Biên lợi nhuận"] = np.where(
        final["Doanh thu thuần"] != 0,
        final["Lợi nhuận"] / final["Doanh thu thuần"],
        np.nan,
    )
    final["Tỷ lệ chiết khấu"] = np.where(
        final["Doanh số"] != 0,
        final["Chiết khấu"] / final["Doanh số"],
        np.nan,
    )
    final["Tỷ lệ hoàn trả"] = np.where(
        final["Doanh số"] != 0,
        final["Giá trị trả lại"] / final["Doanh số"],
        np.nan,
    )
    final["Giá trị TB/dòng"] = final["Doanh thu thuần"]
    return final

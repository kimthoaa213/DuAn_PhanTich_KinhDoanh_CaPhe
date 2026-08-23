import numpy as np
import pandas as pd


def _make_dimension(source: pd.DataFrame, key_col: str, natural_col: str, attrs: list[str]) -> pd.DataFrame:
    """Tạo dimension đơn giản từ mã tự nhiên và các thuộc tính mô tả đi kèm."""
    cols = [natural_col] + [col for col in attrs if col in source.columns]
    dim = source[cols].drop_duplicates(subset=[natural_col]).copy()
    # Null trong khóa phân tích được gom về "Không xác định" để Tableau không bị rỗng nhóm.
    dim[natural_col] = dim[natural_col].astype("string").fillna("Không xác định")
    dim = dim.sort_values(natural_col).reset_index(drop=True)
    # Surrogate key dạng số giúp fact table nhẹ hơn và mô phỏng cấu trúc star schema.
    dim[key_col] = range(1, len(dim) + 1)
    return dim[[key_col] + cols]


def build_dim_date(sales: pd.DataFrame) -> pd.DataFrame:
    """Tạo bảng ngày dùng chung cho phân tích theo năm, quý, tháng."""
    dim = sales[["Ngày chứng từ", "Năm", "Tháng", "Quý", "Năm-Tháng"]].drop_duplicates().copy()
    dim["date_key"] = pd.to_datetime(dim["Ngày chứng từ"]).dt.strftime("%Y%m%d").astype("Int64")
    dim["Tên tháng"] = "Tháng " + dim["Tháng"].astype("Int64").astype(str)
    dim = dim.sort_values("Ngày chứng từ")
    return dim[["date_key", "Ngày chứng từ", "Năm", "Quý", "Tháng", "Tên tháng", "Năm-Tháng"]]


def build_star_schema(sales: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Tách data final thành fact_sales và các bảng dim để Tableau có thể phân tích linh hoạt."""
    fact = sales.copy()
    dim_date = build_dim_date(fact)

    dim_customer = _make_dimension(
        fact,
        "customer_key",
        "Mã khách hàng",
        ["Tên khách hàng", "Nhóm khách hàng"],
    )
    dim_product = _make_dimension(
        fact,
        "product_key",
        "Mã sản phẩm",
        ["Tên sản phẩm", "Nhóm sản phẩm", "Loại sản phẩm"],
    )
    dim_channel = _make_dimension(fact, "channel_key", "Kênh", [])

    fact["date_key"] = fact["Ngày chứng từ"].dt.strftime("%Y%m%d").astype("Int64")
    # Gắn khóa dimension vào fact dựa trên mã khách hàng, mã sản phẩm và kênh.
    fact = fact.merge(dim_customer[["customer_key", "Mã khách hàng"]], on="Mã khách hàng", how="left")
    fact = fact.merge(dim_product[["product_key", "Mã sản phẩm"]], on="Mã sản phẩm", how="left")
    fact = fact.merge(dim_channel[["channel_key", "Kênh"]], on="Kênh", how="left")
    fact["sales_id"] = range(1, len(fact) + 1)

    fact_columns = [
        "sales_id",
        "date_key",
        "customer_key",
        "product_key",
        "channel_key",
        "Số chứng từ",
        "ĐVT",
        "Số lượng",
        "Khối lượng KG",
        "Đơn giá",
        "Doanh số",
        "Chiết khấu",
        "Doanh thu thuần",
        "Số lượng trả lại",
        "Giá trị trả lại",
        "Giá vốn đơn vị",
        "Tổng giá vốn",
        "Lợi nhuận",
        "Biên lợi nhuận",
        "Tỷ lệ chiết khấu",
        "Tỷ lệ hoàn trả",
        "Trả hàng",
        "Giai đoạn",
        "Nguồn dữ liệu",
        "Chi nhánh",
        "Vùng doanh thu",
    ]
    fact_sales = fact[fact_columns].copy()

    # Trả về cả fact/dim để người dùng có thể nối bảng trong Tableau nếu cần phân tích chi tiết.
    return {
        "fact_sales": fact_sales,
        "dim_date": dim_date,
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_channel": dim_channel,
    }


def aggregate_kpi(sales: pd.DataFrame, by_cols: list[str]) -> pd.DataFrame:
    """Tổng hợp KPI theo một hoặc nhiều chiều phân tích."""
    mart = sales.groupby(by_cols, dropna=False).agg(
        **{
            "Doanh thu thuần": ("Doanh thu thuần", "sum"),
            "Lợi nhuận": ("Lợi nhuận", "sum"),
            "Tổng giá vốn": ("Tổng giá vốn", "sum"),
            "Doanh số": ("Doanh số", "sum"),
            "Chiết khấu": ("Chiết khấu", "sum"),
            "Giá trị trả lại": ("Giá trị trả lại", "sum"),
            "Số lượng": ("Số lượng", "sum"),
            "Khối lượng KG": ("Khối lượng KG", "sum"),
            "Số đơn hàng": ("Số chứng từ", "nunique"),
            "Số khách hàng": ("Mã khách hàng", "nunique"),
            "Số sản phẩm": ("Mã sản phẩm", "nunique"),
        }
    ).reset_index()
    # Các tỷ lệ được tính sau aggregation để đúng theo tổng doanh thu/tổng doanh số,
    # không lấy trung bình đơn giản của tỷ lệ từng dòng hóa đơn.
    mart["Biên lợi nhuận"] = mart["Lợi nhuận"] / mart["Doanh thu thuần"].replace(0, np.nan)
    mart["Tỷ lệ chiết khấu"] = mart["Chiết khấu"] / mart["Doanh số"].replace(0, np.nan)
    mart["Tỷ lệ hoàn trả"] = mart["Giá trị trả lại"] / mart["Doanh số"].replace(0, np.nan)
    mart["Giá trị TB/đơn"] = mart["Doanh thu thuần"] / mart["Số đơn hàng"].replace(0, np.nan)
    return mart


def build_customer_pareto(sales: pd.DataFrame) -> pd.DataFrame:
    """Tạo mart Pareto để xem nhóm khách hàng nào đóng góp phần lớn doanh thu theo từng năm."""
    pareto = aggregate_kpi(sales, ["Năm", "Nhóm khách hàng", "Giai đoạn"])
    pareto = pareto.sort_values(["Năm", "Doanh thu thuần"], ascending=[True, False])
    pareto["Tỷ trọng doanh thu"] = pareto.groupby("Năm")["Doanh thu thuần"].transform(lambda x: x / x.sum())
    pareto["Tỷ trọng lũy kế"] = pareto.groupby("Năm")["Tỷ trọng doanh thu"].cumsum()
    pareto["Nhóm Pareto"] = np.where(pareto["Tỷ trọng lũy kế"] <= 0.8, "Top 80%", "Còn lại")
    return pareto


def build_all_marts(sales: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Tạo toàn bộ bảng mart phục vụ dashboard: thời gian, kênh, sản phẩm, vùng, khách hàng."""
    marts = build_star_schema(sales)
    # Mỗi mart trả lời một nhóm câu hỏi dashboard cụ thể.
    # Ví dụ mart_channel_product dùng khi muốn xem doanh thu theo kênh và nhóm sản phẩm.
    marts.update(
        {
            "mart_overview_year": aggregate_kpi(sales, ["Năm", "Giai đoạn"]),
            "mart_time_month": aggregate_kpi(sales, ["Năm", "Tháng", "Năm-Tháng", "Giai đoạn"]),
            "mart_time_quarter": aggregate_kpi(sales, ["Năm", "Quý", "Giai đoạn"]),
            "mart_channel": aggregate_kpi(sales, ["Năm", "Tháng", "Kênh", "Giai đoạn"]),
            "mart_product_group": aggregate_kpi(sales, ["Năm", "Tháng", "Nhóm sản phẩm", "Giai đoạn"]),
            "mart_region": aggregate_kpi(sales, ["Năm", "Tháng", "Vùng doanh thu", "Giai đoạn"]),
            "mart_customer_group": aggregate_kpi(sales, ["Năm", "Tháng", "Nhóm khách hàng", "Giai đoạn"]),
            "mart_channel_product": aggregate_kpi(
                sales, ["Năm", "Tháng", "Kênh", "Nhóm sản phẩm", "Giai đoạn"]
            ),
            "mart_quarter_channel": aggregate_kpi(sales, ["Năm", "Quý", "Kênh", "Giai đoạn"]),
            "mart_pareto_customer_group": build_customer_pareto(sales),
        }
    )
    return marts
 

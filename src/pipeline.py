import pandas as pd

from .config import CLEAN_DIR, EXCEL_OUTPUT_DIR, MART_DIR, MODEL_DATA_DIR, OUTPUT_EXCEL, STAGING_DIR, clear_directory, ensure_directories, get_input_files
from .extract import load_2026_excel, load_cost_excel, load_historical_excel
from .mart import build_all_marts
from .modeling import build_forecast_vs_actual, forecast_revenue_2026, prepare_monthly_revenue_data
from .transform import build_final_sales, clean_cost, clean_historical, clean_sales_2026
from .utils import data_overview, write_table
from .utils import clean_text_series


def run_cleaning_stage() -> dict:
    """Giai đoạn 01: đọc raw, kiểm tra, làm sạch, merge giá vốn và tạo data final."""
    ensure_directories()
    # Chỉ xóa output trung gian/output clean cũ để tránh dùng lẫn kết quả từ lần chạy trước.
    clear_directory(STAGING_DIR)
    clear_directory(CLEAN_DIR)
    files = get_input_files()

    # Extract: đọc nguyên trạng các file Excel đầu vào.
    raw_hist = load_historical_excel(files["historical"])
    raw_2026 = load_2026_excel(files["sales_2026"])
    raw_cost = load_cost_excel(files["cost_2026"])

    # Transform: chuẩn hóa riêng từng nguồn vì 2023-2025, 2026 và giá vốn có schema khác nhau.
    hist_clean = clean_historical(raw_hist)
    cost_clean = clean_cost(raw_cost)
    sales_2026_clean = clean_sales_2026(raw_2026, cost_clean)
    # Sau khi từng nguồn đã sạch, gộp về một bảng final chung để các bước sau dùng thống nhất.
    final_sales = build_final_sales(hist_clean, sales_2026_clean)

    # Lưu staging để có thể kiểm tra từng lớp dữ liệu: raw -> clean riêng nguồn -> final.
    write_table(raw_hist, STAGING_DIR / "raw_sales_2023_2025")
    write_table(raw_2026, STAGING_DIR / "raw_sales_2026")
    write_table(raw_cost, STAGING_DIR / "raw_cost_2026")
    write_table(hist_clean, STAGING_DIR / "sales_2023_2025_clean")
    write_table(cost_clean, STAGING_DIR / "cost_2026_clean")
    write_table(sales_2026_clean, STAGING_DIR / "sales_2026_clean")
    write_table(final_sales, CLEAN_DIR / "sales_final")

    # Bảng overview giúp báo cáo chất lượng dữ liệu: số dòng, số cột, null, duplicate.
    overview = pd.concat(
        [
            data_overview(raw_hist, "raw_sales_2023_2025"),
            data_overview(raw_2026, "raw_sales_2026"),
            data_overview(raw_cost, "raw_cost_2026"),
            data_overview(hist_clean, "sales_2023_2025_clean"),
            data_overview(sales_2026_clean, "sales_2026_clean"),
            data_overview(cost_clean, "cost_2026_clean"),
            data_overview(final_sales, "sales_final"),
        ],
        ignore_index=True,
    )
    write_table(overview, CLEAN_DIR / "data_quality_overview")

    return {
        "raw_hist": raw_hist,
        "raw_2026": raw_2026,
        "raw_cost": raw_cost,
        "hist_clean": hist_clean,
        "sales_2026_clean": sales_2026_clean,
        "cost_clean": cost_clean,
        "final_sales": final_sales,
        "data_quality_overview": overview,
    }


def load_final_sales() -> pd.DataFrame:
    """Đọc data final đã clean và chuẩn hóa lại text để tránh lỗi filter/groupby trong notebook."""
    path = CLEAN_DIR / "sales_final.csv"
    if not path.exists():
        raise FileNotFoundError("Chưa có data/clean/sales_final.csv. Hãy chạy notebook 01 hoặc run_cleaning_stage trước.")
    df = pd.read_csv(path, low_memory=False)
    df["Ngày chứng từ"] = pd.to_datetime(df["Ngày chứng từ"], errors="coerce")
    for col in df.select_dtypes(include=["object"]).columns:
        # CSV mở/ghi qua nhiều công cụ có thể sinh khoảng trắng ẩn; clean lại ở điểm đọc giúp notebook ổn định.
        df[col] = clean_text_series(df[col])
    return df


def run_mart_stage(final_sales: pd.DataFrame | None = None) -> dict:
    """Giai đoạn 02: xây dựng star schema và aggregate data mart từ data clean."""
    ensure_directories()
    clear_directory(MART_DIR)
    if final_sales is None:
        # Cho phép chạy riêng notebook 02 mà không cần giữ biến từ notebook 01.
        final_sales = load_final_sales()
    marts = build_all_marts(final_sales)
    for name, df in marts.items():
        # Mỗi mart được xuất thành một CSV riêng để Tableau kết nối trực tiếp.
        write_table(df, MART_DIR / name)
    return {"final_sales": final_sales, "marts": marts}


def run_modeling_stage(final_sales: pd.DataFrame | None = None) -> dict:
    """Giai đoạn 04: mô hình dự báo doanh thu và mart so sánh forecast vs actual."""
    ensure_directories()
    clear_directory(MODEL_DATA_DIR)
    if final_sales is None:
        final_sales = load_final_sales()
    # Tạo dữ liệu tháng từ 2023-2025, huấn luyện mô hình, rồi dự báo T1-T5/2026.
    monthly, model_data = prepare_monthly_revenue_data(final_sales)
    forecast, artifacts = forecast_revenue_2026(monthly, model_data)
    # Mart forecast_vs_actual là bảng kết luận chính để so sánh trước/sau tái cấu trúc.
    comparison = build_forecast_vs_actual(forecast, final_sales)

    write_table(monthly, MODEL_DATA_DIR / "monthly_model_base")
    write_table(model_data, MODEL_DATA_DIR / "monthly_model_data")
    write_table(forecast, MODEL_DATA_DIR / "forecast_revenue_2026")
    write_table(comparison, MART_DIR / "forecast_vs_actual")
    for name, df in artifacts.items():
        write_table(df, MODEL_DATA_DIR / name)

    return {
        "monthly_model_base": monthly,
        "monthly_model_data": model_data,
        "forecast_revenue_2026": forecast,
        "forecast_vs_actual": comparison,
        "model_artifacts": artifacts,
    }


def export_excel_summary(cleaning: dict, marts: dict, modeling: dict) -> None:
    """Xuất một workbook tổng hợp để nộp kèm hoặc kiểm tra nhanh ngoài Jupyter/Tableau."""
    EXCEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        cleaning["data_quality_overview"].to_excel(writer, sheet_name="data_quality", index=False)
        cleaning["final_sales"].to_excel(writer, sheet_name="sales_final", index=False)
        modeling["forecast_vs_actual"].to_excel(writer, sheet_name="forecast_vs_actual", index=False)
        modeling["monthly_model_base"].to_excel(writer, sheet_name="monthly_model_base", index=False)
        for name, df in modeling["model_artifacts"].items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
        for name, df in marts.items():
            if name != "fact_sales":
                # Excel giới hạn tên sheet 31 ký tự; fact_sales thường quá chi tiết nên không xuất vào workbook.
                df.to_excel(writer, sheet_name=name[:31], index=False)


def run_pipeline() -> dict:
    """Chạy toàn bộ quy trình theo thứ tự: clean -> mart -> modeling -> export."""
    # Thứ tự này rất quan trọng:
    # 1. Clean tạo sales_final chuẩn.
    # 2. Mart chỉ được xây trên sales_final.
    # 3. Model dự báo dùng sales_final và tạo thêm forecast_vs_actual.
    # 4. Export Excel gom các kết quả chính.
    cleaning = run_cleaning_stage()
    mart_result = run_mart_stage(cleaning["final_sales"])
    modeling = run_modeling_stage(cleaning["final_sales"])
    marts = dict(mart_result["marts"])
    marts["forecast_vs_actual"] = modeling["forecast_vs_actual"]
    export_excel_summary(cleaning, marts, modeling)
    return {
        **cleaning,
        "marts": marts,
        **modeling,
        "output_excel": OUTPUT_EXCEL,
    }

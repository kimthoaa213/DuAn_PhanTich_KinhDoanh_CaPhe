from sklearn.base import clone
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import numpy as np
import pandas as pd

try:
    from xgboost import XGBRegressor

    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


FEATURE_REVENUE = [
    "Tháng",
    "Quý",
    "Chỉ số thời gian",
    "Số lượng",
    "Khối lượng KG",
    "Số đơn hàng",
    "Số khách hàng",
    "Số sản phẩm",
    "Tỷ lệ chiết khấu",
    "Giá trị TB/đơn",
    "Tháng_sin",
    "Tháng_cos",
    "Doanh thu trễ 1 tháng",
    "Doanh thu trễ 12 tháng",
    "Doanh thu TB 3 tháng trước",
]


SUM_GROWTH_FEATURES = [
    "Số lượng",
    "Khối lượng KG",
    "Số đơn hàng",
]

AVG_MONTHLY_GROWTH_FEATURES = [
    "Số khách hàng",
    "Số sản phẩm",
]

PERCENT_DELTA_FEATURES = [
    "Tỷ lệ chiết khấu",
]

FORECAST_MONTHS_2026 = [1, 2, 3, 4, 5]


def prepare_monthly_revenue_data(final_sales: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tổng hợp dữ liệu 2023-2025 theo tháng và tạo feature đầu vào cho mô hình doanh thu."""
    # Mục tiêu là dự báo "nếu chưa tái cấu trúc thì 2026 có thể đạt bao nhiêu",
    # nên mô hình chỉ học từ giai đoạn trước tái cấu trúc.
    hist = final_sales[final_sales["Nguồn dữ liệu"] == "2023-2025"].copy()
    monthly = hist.groupby(["Năm", "Tháng", "Quý"]).agg(
        **{
            "Doanh thu thuần": ("Doanh thu thuần", "sum"),
            "Doanh số": ("Doanh số", "sum"),
            "Chiết khấu": ("Chiết khấu", "sum"),
            "Số lượng": ("Số lượng", "sum"),
            "Khối lượng KG": ("Khối lượng KG", "sum"),
            "Số đơn hàng": ("Số chứng từ", "nunique"),
            "Số khách hàng": ("Mã khách hàng", "nunique"),
            "Số sản phẩm": ("Mã sản phẩm", "nunique"),
        }
    ).reset_index()
    monthly = monthly.sort_values(["Năm", "Tháng"]).reset_index(drop=True)
    # Chỉ số thời gian biểu diễn xu hướng dài hạn theo tháng liên tục.
    monthly["Chỉ số thời gian"] = (monthly["Năm"] - monthly["Năm"].min()) * 12 + monthly["Tháng"]
    monthly["Tỷ lệ chiết khấu"] = monthly["Chiết khấu"] / monthly["Doanh số"].replace(0, np.nan)
    monthly["Giá trị TB/đơn"] = monthly["Doanh thu thuần"] / monthly["Số đơn hàng"].replace(0, np.nan)
    # Biến sin/cos giúp mô hình học tính mùa vụ theo tháng.
    monthly["Tháng_sin"] = np.sin(2 * np.pi * monthly["Tháng"] / 12)
    monthly["Tháng_cos"] = np.cos(2 * np.pi * monthly["Tháng"] / 12)
    # Lag/rolling feature dùng doanh thu quá khứ để phản ánh quán tính kinh doanh.
    monthly["Doanh thu trễ 1 tháng"] = monthly["Doanh thu thuần"].shift(1)
    monthly["Doanh thu trễ 12 tháng"] = monthly["Doanh thu thuần"].shift(12)
    monthly["Doanh thu TB 3 tháng trước"] = monthly["Doanh thu thuần"].shift(1).rolling(3).mean()
    # Drop null vì các feature lag đầu chuỗi chưa có dữ liệu quá khứ.
    model_data = monthly.dropna().reset_index(drop=True)
    return monthly, model_data


def candidate_models() -> dict:
    """Danh sách mô hình thử nghiệm; chọn mô hình có MAPE tốt nhất ở bước backtest."""
    models = {
        "Ridge": Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=1.0))]),
        "Random Forest": RandomForestRegressor(n_estimators=300, random_state=42, min_samples_leaf=2),
        "Gradient Boosting": GradientBoostingRegressor(random_state=42),
    }
    if HAS_XGBOOST:
        models["XGBoost"] = XGBRegressor(
            n_estimators=300,
            learning_rate=0.05,
            max_depth=2,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="reg:squarederror",
            random_state=42,
        )
    return models


def backtest_revenue_models(model_data: pd.DataFrame) -> tuple[pd.DataFrame, str, pd.DataFrame]:
    """Train 2024, backtest T1-T5/2025 vì feature lag 12 làm mất năm 2023."""
    train = model_data[model_data["Năm"] <= 2024].copy()
    test = model_data[(model_data["Năm"] == 2025) & (model_data["Tháng"] <= 5)].copy()

    rows = []
    predictions = {}
    for name, model in candidate_models().items():
        # clone để mỗi mô hình được fit độc lập, tránh reuse trạng thái từ lần fit trước.
        model = clone(model)
        model.fit(train[FEATURE_REVENUE], train["Doanh thu thuần"])
        pred = model.predict(test[FEATURE_REVENUE])
        predictions[name] = pred
        rows.append(
            {
                "Mô hình": name,
                "MAE": mean_absolute_error(test["Doanh thu thuần"], pred),
                "MAPE": mean_absolute_percentage_error(test["Doanh thu thuần"], pred),
                "R2": r2_score(test["Doanh thu thuần"], pred),
            }
        )

    metrics = pd.DataFrame(rows).sort_values("MAPE").reset_index(drop=True)
    # Chọn mô hình có MAPE thấp nhất vì bài toán cần sai số tương đối dễ diễn giải cho doanh thu.
    best_model = metrics.loc[0, "Mô hình"]
    backtest = test[["Năm", "Tháng", "Doanh thu thuần"]].copy()
    backtest["Doanh thu dự báo"] = predictions[best_model]
    backtest["Chênh lệch"] = backtest["Doanh thu thuần"] - backtest["Doanh thu dự báo"]
    backtest["Tỷ lệ chênh lệch"] = backtest["Chênh lệch"] / backtest["Doanh thu dự báo"].replace(0, np.nan)
    return metrics, best_model, backtest


def _safe_growth_factor(start_value: float, end_value: float, periods: int = 2) -> float:
    if pd.isna(start_value) or pd.isna(end_value) or start_value <= 0 or end_value <= 0:
        return 1.0
    return float(np.clip((end_value / start_value) ** (1 / periods), 0.7, 1.3))


def _safe_delta(start_value: float, end_value: float) -> float:
    if pd.isna(start_value) or pd.isna(end_value):
        return 0.0
    return float(np.clip(end_value - start_value, -0.05, 0.05))


def _annual_value(monthly: pd.DataFrame, year: int, feature: str, method: str) -> float:
    data = monthly[monthly["Năm"] == year]
    if data.empty:
        return np.nan
    if method == "sum":
        return data[feature].sum()
    if method == "mean":
        return data[feature].mean()
    if method == "avg_order_value":
        orders = data["Số đơn hàng"].sum()
        if orders == 0:
            return np.nan
        return data["Doanh thu thuần"].sum() / orders
    if method == "discount_rate":
        sales = data["Doanh số"].sum()
        if sales == 0:
            return np.nan
        return data["Chiết khấu"].sum() / sales
    raise ValueError(f"Unknown annual method: {method}")


def _build_growth_assumptions(monthly: pd.DataFrame) -> tuple[dict[str, float], dict[str, float], pd.DataFrame]:
    """Tính giả định tăng trưởng từ 2023 đến 2025 để điều chỉnh feature vận hành cho 2026."""
    factors: dict[str, float] = {}
    deltas: dict[str, float] = {}
    rows = []

    for feature in SUM_GROWTH_FEATURES:
        start_value = _annual_value(monthly, 2023, feature, "sum")
        end_value = _annual_value(monthly, 2025, feature, "sum")
        factor = _safe_growth_factor(start_value, end_value)
        factors[feature] = factor
        rows.append(
            {
                "Chỉ số": feature,
                "Cách tính": "Tổng năm",
                "Giá trị 2023": start_value,
                "Giá trị 2025": end_value,
                "Hệ số áp dụng cho 2026": factor,
                "Loại điều chỉnh": "CAGR",
            }
        )

    for feature in AVG_MONTHLY_GROWTH_FEATURES:
        start_value = _annual_value(monthly, 2023, feature, "mean")
        end_value = _annual_value(monthly, 2025, feature, "mean")
        factor = _safe_growth_factor(start_value, end_value)
        factors[feature] = factor
        rows.append(
            {
                "Chỉ số": feature,
                "Cách tính": "Trung bình tháng",
                "Giá trị 2023": start_value,
                "Giá trị 2025": end_value,
                "Hệ số áp dụng cho 2026": factor,
                "Loại điều chỉnh": "CAGR",
            }
        )

    start_value = _annual_value(monthly, 2023, "Giá trị TB/đơn", "avg_order_value")
    end_value = _annual_value(monthly, 2025, "Giá trị TB/đơn", "avg_order_value")
    factors["Giá trị TB/đơn"] = _safe_growth_factor(start_value, end_value)
    rows.append(
        {
            "Chỉ số": "Giá trị TB/đơn",
            "Cách tính": "Tổng doanh thu thuần / tổng số đơn hàng",
            "Giá trị 2023": start_value,
            "Giá trị 2025": end_value,
            "Hệ số áp dụng cho 2026": factors["Giá trị TB/đơn"],
            "Loại điều chỉnh": "CAGR",
        }
    )

    start_value = _annual_value(monthly, 2023, "Tỷ lệ chiết khấu", "discount_rate")
    end_value = _annual_value(monthly, 2025, "Tỷ lệ chiết khấu", "discount_rate")
    deltas["Tỷ lệ chiết khấu"] = _safe_delta(start_value, end_value)
    rows.append(
        {
            "Chỉ số": "Tỷ lệ chiết khấu",
            "Cách tính": "Tổng chiết khấu / tổng doanh số",
            "Giá trị 2023": start_value,
            "Giá trị 2025": end_value,
            "Hệ số áp dụng cho 2026": deltas["Tỷ lệ chiết khấu"],
            "Loại điều chỉnh": "Chênh lệch điểm tỷ lệ",
        }
    )

    return factors, deltas, pd.DataFrame(rows)


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _lookup_revenue(revenue_history: dict[tuple[int, int], float], year: int, month: int) -> float:
    return revenue_history.get((year, month), np.nan)


def _rolling_previous_revenue(revenue_history: dict[tuple[int, int], float], year: int, month: int, window: int = 3) -> float:
    values = []
    current_year, current_month = year, month
    for _ in range(window):
        current_year, current_month = _previous_month(current_year, current_month)
        value = _lookup_revenue(revenue_history, current_year, current_month)
        if not pd.isna(value):
            values.append(value)
    if not values:
        return np.nan
    return float(np.mean(values))


def forecast_revenue_2026(monthly: pd.DataFrame, model_data: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    metrics, best_model_name, backtest = backtest_revenue_models(model_data)
    growth_factors, percent_deltas, growth_assumptions = _build_growth_assumptions(monthly)

    model = clone(candidate_models()[best_model_name])
    # Sau khi chọn mô hình tốt nhất bằng backtest, fit lại trên toàn bộ dữ liệu model 2023-2025.
    model.fit(model_data[FEATURE_REVENUE], model_data["Doanh thu thuần"])

    base_future = monthly[(monthly["Năm"] == 2025) & (monthly["Tháng"].isin(FORECAST_MONTHS_2026))].copy()
    base_future = base_future.sort_values("Tháng").reset_index(drop=True)
    if base_future.empty:
        raise ValueError("Không đủ dữ liệu T1-T5/2025 để tạo feature dự báo 2026.")

    # Lưu doanh thu lịch sử để các biến lag của 2026 giữ đúng ý nghĩa:
    # lag 12 là cùng kỳ 2025, lag 1 và trung bình 3 tháng được cập nhật tuần tự theo dự báo vừa sinh.
    revenue_history = {
        (int(row["Năm"]), int(row["Tháng"])): float(row["Doanh thu thuần"])
        for _, row in monthly.dropna(subset=["Doanh thu thuần"]).iterrows()
    }

    future_rows = []
    for _, base_row in base_future.iterrows():
        row = base_row.copy()
        month = int(row["Tháng"])
        row["Năm"] = 2026
        row["Quý"] = int(np.ceil(month / 3))
        row["Chỉ số thời gian"] = (2026 - monthly["Năm"].min()) * 12 + month
        row["Tháng_sin"] = np.sin(2 * np.pi * month / 12)
        row["Tháng_cos"] = np.cos(2 * np.pi * month / 12)

        for feature, factor in growth_factors.items():
            row[feature] = row[feature] * factor
        for feature, delta in percent_deltas.items():
            row[feature] = max(row[feature] + delta, 0)

        previous_year, previous_month = _previous_month(2026, month)
        row["Doanh thu trễ 1 tháng"] = _lookup_revenue(revenue_history, previous_year, previous_month)
        row["Doanh thu trễ 12 tháng"] = _lookup_revenue(revenue_history, 2025, month)
        row["Doanh thu TB 3 tháng trước"] = _rolling_previous_revenue(revenue_history, 2026, month)

        feature_frame = pd.DataFrame([row[FEATURE_REVENUE]])
        predicted_revenue = float(np.clip(model.predict(feature_frame)[0], 0, None))
        row["Doanh thu dự báo"] = predicted_revenue
        row["Doanh thu thuần"] = np.nan
        revenue_history[(2026, month)] = predicted_revenue
        future_rows.append(row)

    future = pd.DataFrame(future_rows)
    future["Năm"] = future["Năm"].astype(int)
    future["Tháng"] = future["Tháng"].astype(int)
    future["Quý"] = future["Quý"].astype(int)
    forecast = future[["Năm", "Tháng", "Doanh thu dự báo"]].copy()
    artifacts = {
        "model_revenue_metrics": metrics,
        "backtest_revenue": backtest,
        "forecast_feature_assumptions": growth_assumptions,
        "forecast_feature_2026": future[["Năm", *FEATURE_REVENUE, "Doanh thu dự báo"]].copy(),
    }
    return forecast, artifacts


def build_forecast_vs_actual(forecast: pd.DataFrame, final_sales: pd.DataFrame) -> pd.DataFrame:
    """Ghép dự báo T1-T5/2026 với thực tế 2026 để đánh giá hiệu quả tái cấu trúc."""
    # Lấy thực tế theo Năm == 2026 thay vì phụ thuộc cột nguồn dữ liệu,
    # tránh lỗi nếu cột nguồn có khoảng trắng hoặc biến thể nhập liệu.
    actual = final_sales[
        (final_sales["Năm"] == 2026)
        & (final_sales["Tháng"].between(1, 5))
    ]
    actual_monthly = actual.groupby(["Năm", "Tháng"]).agg(
        **{
            "Doanh thu thực tế": ("Doanh thu thuần", "sum"),
            "Lợi nhuận thực tế": ("Lợi nhuận", "sum"),
            "Tổng giá vốn": ("Tổng giá vốn", "sum"),
            "Doanh số thực tế": ("Doanh số", "sum"),
            "Chiết khấu": ("Chiết khấu", "sum"),
            "Giá trị trả lại": ("Giá trị trả lại", "sum"),
            "Số đơn hàng": ("Số chứng từ", "nunique"),
            "Số khách hàng": ("Mã khách hàng", "nunique"),
            "Số sản phẩm": ("Mã sản phẩm", "nunique"),
        }
    ).reset_index()
    comparison = forecast.merge(actual_monthly, on=["Năm", "Tháng"], how="left")
    # Chênh lệch dương nghĩa là thực tế sau tái cấu trúc cao hơn kịch bản dự báo.
    comparison["Chênh lệch doanh thu"] = comparison["Doanh thu thực tế"] - comparison["Doanh thu dự báo"]
    comparison["Tỷ lệ chênh lệch doanh thu"] = (
        comparison["Chênh lệch doanh thu"] / comparison["Doanh thu dự báo"].replace(0, np.nan)
    )
    comparison["Biên lợi nhuận thực tế"] = (
        comparison["Lợi nhuận thực tế"] / comparison["Doanh thu thực tế"].replace(0, np.nan)
    )
    return comparison

from datetime import datetime
import json
import os
from pathlib import Path
import re
from urllib import request
from urllib.error import HTTPError, URLError

import numpy as np
import pandas as pd

from .config import AI_AGENT_DIR, PROJECT_DIR, ensure_directories


UPDATE_INSIGHT_FILE = AI_AGENT_DIR / "update_insight.csv"
DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"

UPDATE_INSIGHT_COLUMNS = [
    "update_id",
    "update_time",
    "new_order_file",
    "input_rows",
    "appended_rows",
    "duplicate_rows",
    "uploaded_cloud",
    "status",
    "severity",
    "revenue_before",
    "revenue_after",
    "revenue_change",
    "revenue_change_pct",
    "profit_before",
    "profit_after",
    "profit_change",
    "profit_change_pct",
    "margin_before",
    "margin_after",
    "margin_change_point",
    "discount_rate_before",
    "discount_rate_after",
    "discount_rate_change_point",
    "return_rate_before",
    "return_rate_after",
    "return_rate_change_point",
    "order_count_before",
    "order_count_after",
    "order_count_change",
    "order_count_change_pct",
    "customer_count_before",
    "customer_count_after",
    "customer_count_change",
    "customer_count_change_pct",
    "avg_order_value_before",
    "avg_order_value_after",
    "avg_order_value_change",
    "avg_order_value_change_pct",
    "ai_error",
    "insight",
    "recommendation",
    "created_at",
]


def load_env_file(path: Path | None = None) -> None:
    """Load bien moi truong tu .env cuc bo, khong yeu cau python-dotenv."""
    env_path = path or PROJECT_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _safe_sum(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns or df.empty:
        return 0.0
    return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def _safe_nunique(df: pd.DataFrame, column: str) -> int:
    if column not in df.columns or df.empty:
        return 0
    return int(df[column].nunique(dropna=True))


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0 or pd.isna(denominator):
        return np.nan
    return float(numerator / denominator)


def build_kpi_snapshot(sales: pd.DataFrame) -> dict[str, float]:
    """Tinh snapshot KPI tong quan tai mot thoi diem."""
    revenue = _safe_sum(sales, "Doanh thu thuần")
    gross_sales = _safe_sum(sales, "Doanh số")
    discount = _safe_sum(sales, "Chiết khấu")
    return_value = _safe_sum(sales, "Giá trị trả lại")
    profit = _safe_sum(sales, "Lợi nhuận")
    orders = _safe_nunique(sales, "Số chứng từ")
    customers = _safe_nunique(sales, "Mã khách hàng")

    return {
        "revenue": revenue,
        "profit": profit,
        "margin": _safe_ratio(profit, revenue),
        "discount_rate": _safe_ratio(discount, gross_sales),
        "return_rate": _safe_ratio(return_value, gross_sales),
        "order_count": orders,
        "customer_count": customers,
        "avg_order_value": _safe_ratio(revenue, orders),
    }


def compare_snapshots(before: dict[str, float], after: dict[str, float]) -> dict[str, float]:
    changes = {}
    for key, before_value in before.items():
        after_value = after.get(key, np.nan)
        changes[f"{key}_before"] = before_value
        changes[f"{key}_after"] = after_value
        if key in {"margin", "discount_rate", "return_rate"}:
            changes[f"{key}_change_point"] = after_value - before_value
        else:
            absolute_change = after_value - before_value
            changes[f"{key}_change"] = absolute_change
            changes[f"{key}_change_pct"] = _safe_ratio(absolute_change, before_value)
    return changes


def evaluate_update(changes: dict[str, float], appended_rows: int) -> tuple[str, str]:
    if appended_rows == 0:
        return "neutral", "low"

    revenue_pct = changes.get("revenue_change_pct", 0)
    profit_pct = changes.get("profit_change_pct", 0)
    margin_point = changes.get("margin_change_point", 0)
    discount_point = changes.get("discount_rate_change_point", 0)
    return_point = changes.get("return_rate_change_point", 0)

    negative_signal = (
        revenue_pct <= -0.03
        or profit_pct <= -0.03
        or margin_point <= -0.03
        or discount_point >= 0.03
        or return_point >= 0.03
    )
    positive_signal = (
        revenue_pct >= 0.03
        or profit_pct >= 0.03
        or margin_point >= 0.03
    ) and margin_point > -0.03 and return_point < 0.03

    if negative_signal:
        status = "negative"
    elif positive_signal:
        status = "positive"
    else:
        status = "neutral"

    max_abs_signal = max(
        abs(value)
        for value in [revenue_pct or 0, profit_pct or 0, margin_point or 0, discount_point or 0, return_point or 0]
    )
    if max_abs_signal >= 0.10:
        severity = "high"
    elif max_abs_signal >= 0.03:
        severity = "medium"
    else:
        severity = "low"
    return status, severity


def _format_money(value: float) -> str:
    if pd.isna(value):
        return "khong xac dinh"
    return f"{value:,.0f} VND"


def _format_pct(value: float) -> str:
    if pd.isna(value):
        return "khong xac dinh"
    return f"{value * 100:.2f}%"


def build_prompt(payload: dict) -> str:
    return f"""
Ban la AI Business Analyst cho dashboard ban hang. Hay viet insight tieng Viet ngan gon dua tren ket qua update hoa don moi.

Yeu cau:
- Khong tu tinh lai so lieu ngoai cac so duoc cung cap.
- Viet theo goc nhin kinh doanh, de hien thi tren Tableau.
- Neu doanh thu tang nhung bien loi nhuan giam, can neu ro rui ro.
- Tra ve JSON hop le, khong markdown, khong giai thich ngoai JSON.

Schema JSON:
{{
  "status": "positive|neutral|negative",
  "severity": "low|medium|high",
  "insight": "1-3 cau tom tat tac dong cua lan update",
  "recommendation": "1 cau goi y hanh dong hoac theo doi"
}}

Du lieu update:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()


def call_gemini_insight(prompt: str) -> dict:
    load_env_file()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Thieu GEMINI_API_KEY trong bien moi truong hoac file .env.")
    model = os.environ.get("AI_AGENT_MODEL", DEFAULT_GEMINI_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    data = json.dumps(body).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=45) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API loi HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Khong ket noi duoc Gemini API: {exc}") from exc

    text = response_data["candidates"][0]["content"]["parts"][0]["text"]
    return parse_llm_json(text)


def parse_llm_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def fallback_insight(row: dict) -> dict:
    if row["appended_rows"] == 0:
        return {
            "status": "neutral",
            "severity": "low",
            "insight": "Lan cap nhat khong ghi nhan dong hoa don moi do du lieu dau vao bi trung hoac khong co dong hop le.",
            "recommendation": "Kiem tra lai file hoa don moi neu ky vong co phat sinh can cap nhat.",
        }

    revenue_change = _format_money(row["revenue_change"])
    revenue_pct = _format_pct(row["revenue_change_pct"])
    profit_pct = _format_pct(row["profit_change_pct"])
    margin_point = _format_pct(row["margin_change_point"])
    return {
        "status": row["status"],
        "severity": row["severity"],
        "insight": (
            f"Sau lan cap nhat, he thong append {row['appended_rows']} dong hoa don moi. "
            f"Doanh thu thay doi {revenue_change}, tuong ung {revenue_pct}; "
            f"loi nhuan thay doi {profit_pct} va bien loi nhuan thay doi {margin_point}."
        ),
        "recommendation": "Theo doi them cac KPI loi nhuan, chiet khau va hoan tra tren dashboard de danh gia chat luong tang truong.",
    }


def build_ai_update_insight(
    before_sales: pd.DataFrame,
    after_sales: pd.DataFrame,
    report: dict,
    new_orders_path: Path | str,
    uploaded_cloud: bool = False,
    use_llm: bool = True,
) -> pd.DataFrame:
    before = build_kpi_snapshot(before_sales)
    after = build_kpi_snapshot(after_sales)
    changes = compare_snapshots(before, after)
    status, severity = evaluate_update(changes, int(report.get("appended_rows", 0)))

    now = datetime.now()
    update_time = now.strftime("%Y-%m-%d %H:%M:%S")
    update_id = now.strftime("%Y%m%d_%H%M%S")
    duplicate_rows = int(report.get("duplicate_with_existing_rows", 0)) + int(report.get("duplicate_inside_new_file_rows", 0))

    row = {
        "update_id": update_id,
        "update_time": update_time,
        "new_order_file": str(new_orders_path),
        "input_rows": int(report.get("raw_new_rows", 0)),
        "appended_rows": int(report.get("appended_rows", 0)),
        "duplicate_rows": duplicate_rows,
        "uploaded_cloud": bool(uploaded_cloud),
        "status": status,
        "severity": severity,
        **changes,
    }

    prompt_payload = {
        "update": {
            "update_id": update_id,
            "update_time": update_time,
            "input_rows": row["input_rows"],
            "appended_rows": row["appended_rows"],
            "duplicate_rows": row["duplicate_rows"],
            "uploaded_cloud": row["uploaded_cloud"],
        },
        "kpi_changes": {
            "revenue_before": _format_money(row["revenue_before"]),
            "revenue_after": _format_money(row["revenue_after"]),
            "revenue_change": _format_money(row["revenue_change"]),
            "revenue_change_pct": _format_pct(row["revenue_change_pct"]),
            "profit_before": _format_money(row["profit_before"]),
            "profit_after": _format_money(row["profit_after"]),
            "profit_change": _format_money(row["profit_change"]),
            "profit_change_pct": _format_pct(row["profit_change_pct"]),
            "margin_before": _format_pct(row["margin_before"]),
            "margin_after": _format_pct(row["margin_after"]),
            "margin_change_point": _format_pct(row["margin_change_point"]),
            "discount_rate_change_point": _format_pct(row["discount_rate_change_point"]),
            "return_rate_change_point": _format_pct(row["return_rate_change_point"]),
        },
        "initial_rule_evaluation": {
            "status": status,
            "severity": severity,
        },
    }

    try:
        llm_result = call_gemini_insight(build_prompt(prompt_payload)) if use_llm else fallback_insight(row)
    except Exception as exc:
        llm_result = fallback_insight(row)
        row["ai_error"] = str(exc)
    else:
        row["ai_error"] = ""

    row["status"] = llm_result.get("status", status)
    row["severity"] = llm_result.get("severity", severity)
    row["insight"] = llm_result.get("insight", "")
    row["recommendation"] = llm_result.get("recommendation", "")
    row["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return pd.DataFrame([row])


def append_ai_update_insight(insight_df: pd.DataFrame) -> Path:
    ensure_directories()
    AI_AGENT_DIR.mkdir(parents=True, exist_ok=True)
    if UPDATE_INSIGHT_FILE.exists():
        existing = pd.read_csv(UPDATE_INSIGHT_FILE, low_memory=False)
        output = pd.concat([existing, insight_df], ignore_index=True)
    else:
        output = insight_df.copy()
    output.to_csv(UPDATE_INSIGHT_FILE, index=False, encoding="utf-8-sig")
    return UPDATE_INSIGHT_FILE


def reset_ai_update_insight_file() -> Path:
    """Lam rong file AI Insight local nhung van giu day du cot cho lan append sau."""
    ensure_directories()
    AI_AGENT_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(columns=UPDATE_INSIGHT_COLUMNS).to_csv(
        UPDATE_INSIGHT_FILE,
        index=False,
        encoding="utf-8-sig",
    )
    return UPDATE_INSIGHT_FILE

import html
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas as pd

from .ai_agent import load_env_file


SEVERITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
}


def _parse_recipients(value: str | None) -> list[str]:
    if not value:
        return []
    normalized = value.replace(";", ",")
    return [email.strip() for email in normalized.split(",") if email.strip()]


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _format_money(value) -> str:
    value = pd.to_numeric(value, errors="coerce")
    if pd.isna(value):
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:,.0f} VND"


def _format_pct(value) -> str:
    value = pd.to_numeric(value, errors="coerce")
    if pd.isna(value):
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.2f}%"


def _format_point(value) -> str:
    value = pd.to_numeric(value, errors="coerce")
    if pd.isna(value):
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value * 100:.2f} điểm %"


def should_send_email(insight_row: dict) -> bool:
    """Kiem tra dieu kien gui email dua tren cau hinh .env va ket qua AI."""
    min_severity = os.environ.get("EMAIL_SEND_MIN_SEVERITY", "low").strip().lower()
    status = str(insight_row.get("status", "")).strip().lower()
    severity = str(insight_row.get("severity", "low")).strip().lower()

    if _env_bool("EMAIL_SEND_NEGATIVE_ONLY", default=False) and status != "negative":
        return False

    min_rank = SEVERITY_RANK.get(min_severity, SEVERITY_RANK["low"])
    current_rank = SEVERITY_RANK.get(severity, SEVERITY_RANK["low"])
    return current_rank >= min_rank


def build_email_subject(insight_row: dict) -> str:
    update_id = str(insight_row.get("update_id", "unknown"))
    status = str(insight_row.get("status", "neutral")).upper()
    severity = str(insight_row.get("severity", "low")).upper()
    return f"[BI Alert] Update {update_id} | {status} | {severity}"


def build_email_body(insight_row: dict) -> str:
    """Tao noi dung email HTML tu mot dong AI Insight."""
    status = html.escape(str(insight_row.get("status", "neutral")))
    severity = html.escape(str(insight_row.get("severity", "low")))
    insight = html.escape(str(insight_row.get("insight", "")))
    recommendation = html.escape(str(insight_row.get("recommendation", "")))
    ai_error = str(insight_row.get("ai_error", "") or "").strip()

    rows = [
        ("Thời gian cập nhật", insight_row.get("update_time", "")),
        ("File hóa đơn mới", insight_row.get("new_order_file", "")),
        ("Số dòng đầu vào", f"{int(insight_row.get('input_rows', 0)):,}"),
        ("Số dòng append", f"{int(insight_row.get('appended_rows', 0)):,}"),
        ("Số dòng trùng", f"{int(insight_row.get('duplicate_rows', 0)):,}"),
        ("Đã upload cloud", str(bool(insight_row.get("uploaded_cloud", False)))),
    ]

    kpi_rows = [
        (
            "Doanh thu thuần",
            _format_money(insight_row.get("revenue_before")),
            _format_money(insight_row.get("revenue_after")),
            _format_money(insight_row.get("revenue_change")),
            _format_pct(insight_row.get("revenue_change_pct")),
        ),
        (
            "Lợi nhuận",
            _format_money(insight_row.get("profit_before")),
            _format_money(insight_row.get("profit_after")),
            _format_money(insight_row.get("profit_change")),
            _format_pct(insight_row.get("profit_change_pct")),
        ),
        (
            "Biên lợi nhuận",
            _format_pct(insight_row.get("margin_before")),
            _format_pct(insight_row.get("margin_after")),
            _format_point(insight_row.get("margin_change_point")),
            "",
        ),
        (
            "Tỷ lệ chiết khấu",
            _format_pct(insight_row.get("discount_rate_before")),
            _format_pct(insight_row.get("discount_rate_after")),
            _format_point(insight_row.get("discount_rate_change_point")),
            "",
        ),
        (
            "Tỷ lệ hoàn trả",
            _format_pct(insight_row.get("return_rate_before")),
            _format_pct(insight_row.get("return_rate_after")),
            _format_point(insight_row.get("return_rate_change_point")),
            "",
        ),
        (
            "Số đơn hàng",
            f"{int(insight_row.get('order_count_before', 0)):,}",
            f"{int(insight_row.get('order_count_after', 0)):,}",
            f"{int(insight_row.get('order_count_change', 0)):+,}",
            _format_pct(insight_row.get("order_count_change_pct")),
        ),
        (
            "Số khách hàng",
            f"{int(insight_row.get('customer_count_before', 0)):,}",
            f"{int(insight_row.get('customer_count_after', 0)):,}",
            f"{int(insight_row.get('customer_count_change', 0)):+,}",
            _format_pct(insight_row.get("customer_count_change_pct")),
        ),
        (
            "Giá trị TB/đơn",
            _format_money(insight_row.get("avg_order_value_before")),
            _format_money(insight_row.get("avg_order_value_after")),
            _format_money(insight_row.get("avg_order_value_change")),
            _format_pct(insight_row.get("avg_order_value_change_pct")),
        ),
    ]

    info_html = "".join(
        f"<tr><td>{html.escape(label)}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
    )
    kpi_html = "".join(
        "<tr>"
        f"<td>{html.escape(metric)}</td>"
        f"<td>{html.escape(before)}</td>"
        f"<td>{html.escape(after)}</td>"
        f"<td>{html.escape(change)}</td>"
        f"<td>{html.escape(change_pct)}</td>"
        "</tr>"
        for metric, before, after, change, change_pct in kpi_rows
    )
    ai_error_html = ""
    if ai_error:
        ai_error_html = f"""
        <p style="color:#9a3412;"><strong>Ghi chú:</strong> AI API có lỗi, nội dung có thể được tạo bằng fallback.</p>
        <pre style="white-space:pre-wrap;background:#fff7ed;padding:10px;border:1px solid #fed7aa;">{html.escape(ai_error)}</pre>
        """

    return f"""
    <html>
      <body style="font-family:Arial,sans-serif;color:#1f2937;line-height:1.45;">
        <h2 style="margin-bottom:4px;">BI Update Notification</h2>
        <p style="margin-top:0;">Trạng thái: <strong>{status}</strong> | Mức độ: <strong>{severity}</strong></p>

        <h3>Thông tin cập nhật</h3>
        <table cellpadding="8" cellspacing="0" border="1" style="border-collapse:collapse;border-color:#d1d5db;">
          {info_html}
        </table>

        <h3>So sánh KPI trước và sau cập nhật</h3>
        <table cellpadding="8" cellspacing="0" border="1" style="border-collapse:collapse;border-color:#d1d5db;">
          <tr style="background:#f3f4f6;">
            <th>KPI</th>
            <th>Trước cập nhật</th>
            <th>Sau cập nhật</th>
            <th>Thay đổi</th>
            <th>% thay đổi</th>
          </tr>
          {kpi_html}
        </table>

        <h3>AI Insight</h3>
        <p>{insight}</p>

        <h3>Recommendation</h3>
        <p>{recommendation}</p>
        {ai_error_html}
      </body>
    </html>
    """


def send_email(subject: str, html_body: str) -> list[str]:
    """Gui email qua SMTP, doc cau hinh tu .env."""
    load_env_file()
    smtp_host = os.environ.get("SMTP_HOST", "").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_password = os.environ.get("SMTP_PASSWORD", "").strip().replace(" ", "")
    email_from = os.environ.get("EMAIL_FROM", smtp_user).strip()
    recipients = _parse_recipients(os.environ.get("EMAIL_TO"))
    cc_recipients = _parse_recipients(os.environ.get("EMAIL_CC"))

    missing = [
        name
        for name, value in {
            "SMTP_HOST": smtp_host,
            "SMTP_USER": smtp_user,
            "SMTP_PASSWORD": smtp_password,
            "EMAIL_FROM": email_from,
            "EMAIL_TO": recipients,
        }.items()
        if not value
    ]
    if missing:
        raise RuntimeError(f"Thieu cau hinh email trong .env: {', '.join(missing)}")

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = email_from
    message["To"] = ", ".join(recipients)
    if cc_recipients:
        message["Cc"] = ", ".join(cc_recipients)
    message.attach(MIMEText(html_body, "html", "utf-8"))

    all_recipients = recipients + cc_recipients
    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(email_from, all_recipients, message.as_string())
    return all_recipients


def notify_update_insight(insight_df: pd.DataFrame) -> dict:
    """Gui email tu dong cho dong AI Insight moi nhat. Loi email khong lam dung pipeline."""
    load_env_file()
    if insight_df.empty:
        return {"sent": False, "reason": "empty_insight"}

    insight_row = insight_df.iloc[-1].to_dict()
    if not should_send_email(insight_row):
        return {"sent": False, "reason": "filtered_by_email_rule"}

    try:
        subject = build_email_subject(insight_row)
        body = build_email_body(insight_row)
        recipients = send_email(subject, body)
    except Exception as exc:
        return {"sent": False, "error": str(exc)}
    return {"sent": True, "recipients": recipients}

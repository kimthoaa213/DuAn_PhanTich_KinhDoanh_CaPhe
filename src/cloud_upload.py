from pathlib import Path
import tempfile
from urllib.parse import quote_plus

import pandas as pd
from psycopg2 import sql
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.types import Boolean, Date, Float, Integer, Text

from .ai_agent import UPDATE_INSIGHT_COLUMNS
from .config import CLEAN_DIR, MART_DIR, MODEL_DATA_DIR


DB_USER = "postgres.txfkgmqfnfahoxrcoiig"
DB_PASSWORD = "phamquanghop"
DB_HOST = "aws-1-ap-southeast-1.pooler.supabase.com"
DB_PORT = "5432"
DB_NAME = "postgres"
DATE_COLUMNS = {"Ngày chứng từ"}


SUMMARY_CLOUD_TABLES = {
    "data_quality_overview": ("audit", CLEAN_DIR / "data_quality_overview.csv"),
    "dim_channel": ("dw", MART_DIR / "dim_channel.csv"),
    "dim_customer": ("dw", MART_DIR / "dim_customer.csv"),
    "dim_date": ("dw", MART_DIR / "dim_date.csv"),
    "dim_product": ("dw", MART_DIR / "dim_product.csv"),
    "fact_sales": ("dw", MART_DIR / "fact_sales.csv"),
    "forecast_vs_actual": ("mart", MART_DIR / "forecast_vs_actual.csv"),
    "mart_channel": ("mart", MART_DIR / "mart_channel.csv"),
    "mart_channel_product": ("mart", MART_DIR / "mart_channel_product.csv"),
    "mart_customer_group": ("mart", MART_DIR / "mart_customer_group.csv"),
    "mart_overview_year": ("mart", MART_DIR / "mart_overview_year.csv"),
    "mart_pareto_customer_group": ("mart", MART_DIR / "mart_pareto_customer_group.csv"),
    "mart_product_group": ("mart", MART_DIR / "mart_product_group.csv"),
    "mart_quarter_channel": ("mart", MART_DIR / "mart_quarter_channel.csv"),
    "mart_region": ("mart", MART_DIR / "mart_region.csv"),
    "mart_time_month": ("mart", MART_DIR / "mart_time_month.csv"),
    "mart_time_quarter": ("mart", MART_DIR / "mart_time_quarter.csv"),
    "backtest_revenue": ("model", MODEL_DATA_DIR / "backtest_revenue.csv"),
    "forecast_feature_2026": ("model", MODEL_DATA_DIR / "forecast_feature_2026.csv"),
    "forecast_feature_assumptions": ("model", MODEL_DATA_DIR / "forecast_feature_assumptions.csv"),
    "forecast_revenue_2026": ("model", MODEL_DATA_DIR / "forecast_revenue_2026.csv"),
    "model_revenue_metrics": ("model", MODEL_DATA_DIR / "model_revenue_metrics.csv"),
    "monthly_model_base": ("model", MODEL_DATA_DIR / "monthly_model_base.csv"),
    "monthly_model_data": ("model", MODEL_DATA_DIR / "monthly_model_data.csv"),
}


LARGE_CLOUD_TABLES = {
    "sales_final": ("clean", CLEAN_DIR / "sales_final.csv"),
}

AI_UPDATE_INSIGHT_DTYPE = {
    "update_id": Text(),
    "update_time": Text(),
    "new_order_file": Text(),
    "input_rows": Integer(),
    "appended_rows": Integer(),
    "duplicate_rows": Integer(),
    "uploaded_cloud": Boolean(),
    "status": Text(),
    "severity": Text(),
    "revenue_before": Float(),
    "revenue_after": Float(),
    "revenue_change": Float(),
    "revenue_change_pct": Float(),
    "profit_before": Float(),
    "profit_after": Float(),
    "profit_change": Float(),
    "profit_change_pct": Float(),
    "margin_before": Float(),
    "margin_after": Float(),
    "margin_change_point": Float(),
    "discount_rate_before": Float(),
    "discount_rate_after": Float(),
    "discount_rate_change_point": Float(),
    "return_rate_before": Float(),
    "return_rate_after": Float(),
    "return_rate_change_point": Float(),
    "order_count_before": Integer(),
    "order_count_after": Integer(),
    "order_count_change": Integer(),
    "order_count_change_pct": Float(),
    "customer_count_before": Integer(),
    "customer_count_after": Integer(),
    "customer_count_change": Integer(),
    "customer_count_change_pct": Float(),
    "avg_order_value_before": Float(),
    "avg_order_value_after": Float(),
    "avg_order_value_change": Float(),
    "avg_order_value_change_pct": Float(),
    "ai_error": Text(),
    "insight": Text(),
    "recommendation": Text(),
    "created_at": Text(),
}

SALES_FINAL_COMPARE_COLUMNS = [
    "Ngày chứng từ",
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
]


def create_cloud_engine() -> Engine:
    """Tạo kết nối Supabase PostgreSQL, tách riêng khỏi pipeline local."""
    password = quote_plus(DB_PASSWORD)
    url = f"postgresql+psycopg2://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url, pool_pre_ping=True)


def check_cloud_connection(engine: Engine) -> None:
    """Kiểm tra kết nối trước khi upload bảng."""
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version();")).scalar_one()
    print("Ket noi Supabase thanh cong.")
    print(version)


def ensure_schema(engine: Engine, schema_name: str) -> None:
    """Tạo schema đích nếu chưa tồn tại."""
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))


def read_csv_for_cloud(path: Path) -> pd.DataFrame:
    """Đọc CSV output local để upload; CSV vẫn được giữ làm backup."""
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file de upload: {path}")
    return pd.read_csv(path, low_memory=False)


def create_empty_table_from_csv(engine: Engine, schema_name: str, table_name: str, path: Path, if_exists: str) -> int:
    """Tạo schema bảng từ CSV trước khi nạp dữ liệu bằng COPY."""
    sample = pd.read_csv(path, nrows=5000, low_memory=False)
    dtype = {}
    for column in sample.columns:
        if column in DATE_COLUMNS:
            sample[column] = pd.to_datetime(sample[column], errors="coerce").dt.date
            dtype[column] = Date()
        if sample[column].isna().all():
            sample[column] = sample[column].astype("string")
    sample.head(0).to_sql(table_name, engine, schema=schema_name, if_exists=if_exists, index=False, dtype=dtype)
    with path.open(encoding="utf-8-sig") as file_obj:
        return int(sum(1 for _ in file_obj) - 1)


def copy_csv_to_postgres(engine: Engine, schema_name: str, table_name: str, path: Path) -> None:
    """Nạp CSV vào PostgreSQL bằng COPY, nhanh hơn pandas.to_sql cho bảng lớn."""
    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cursor:
            copy_sql = sql.SQL("COPY {}.{} FROM STDIN WITH CSV HEADER").format(
                sql.Identifier(schema_name),
                sql.Identifier(table_name),
            )
            with path.open("r", encoding="utf-8-sig", newline="") as file_obj:
                cursor.copy_expert(copy_sql, file_obj)
        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        raw_conn.close()


def upload_table(
    engine: Engine,
    schema_name: str,
    table_name: str,
    path: Path,
    if_exists: str = "replace",
    show_path: bool = True,
) -> None:
    """Upload một CSV thành bảng PostgreSQL."""
    if not path.exists():
        raise FileNotFoundError(f"Khong tim thay file de upload: {path}")
    ensure_schema(engine, schema_name)
    row_count = create_empty_table_from_csv(engine, schema_name, table_name, path, if_exists)
    copy_csv_to_postgres(engine, schema_name, table_name, path)
    if show_path:
        print(f"Da upload {schema_name}.{table_name}: {row_count:,} dong tu {path}", flush=True)
    else:
        print(f"Da nap bang tam {schema_name}.{table_name}: {row_count:,} dong.", flush=True)


def upload_all_tables(if_exists: str = "replace", include_large_tables: bool = False) -> None:
    """Upload bảng thống kê lên Supabase; bảng lớn được để tùy chọn để không làm nặng cloud."""
    engine = create_cloud_engine()
    try:
        check_cloud_connection(engine)
        tables = dict(SUMMARY_CLOUD_TABLES)
        if include_large_tables:
            tables.update(LARGE_CLOUD_TABLES)

        for table_name, (schema_name, path) in tables.items():
            print(f"Dang upload {schema_name}.{table_name}...", flush=True)
            upload_table(engine, schema_name, table_name, path, if_exists=if_exists)
        reset_ai_update_insight_table(engine)
        print("Hoan tat upload du lieu len Supabase.", flush=True)
    finally:
        engine.dispose()


def cloud_table_exists(engine: Engine, schema_name: str, table_name: str) -> bool:
    """Kiem tra bang da ton tai tren Supabase hay chua."""
    with engine.connect() as conn:
        return bool(
            conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE table_schema = :schema_name
                          AND table_name = :table_name
                    )
                    """
                ),
                {"schema_name": schema_name, "table_name": table_name},
            ).scalar_one()
        )


def cloud_column_exists(engine: Engine, schema_name: str, table_name: str, column_name: str) -> bool:
    """Kiem tra cot khoa incremental da co tren bang cloud hay chua."""
    with engine.connect() as conn:
        return bool(
            conn.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = :schema_name
                          AND table_name = :table_name
                          AND column_name = :column_name
                    )
                    """
                ),
                {"schema_name": schema_name, "table_name": table_name, "column_name": column_name},
            ).scalar_one()
        )


def ensure_cloud_columns(engine: Engine, schema_name: str, table_name: str, columns: list[str]) -> None:
    """Dam bao bang cloud co du cac cot sap append."""
    with engine.begin() as conn:
        for column in columns:
            if not cloud_column_exists(engine, schema_name, table_name, column):
                conn.execute(text(f'ALTER TABLE "{schema_name}"."{table_name}" ADD COLUMN "{column}" TEXT'))


def read_cloud_column_types(engine: Engine, schema_name: str, table_name: str) -> dict[str, str]:
    """Doc kieu du lieu cua bang dich de cast du lieu tu staging table khi append."""
    query = text(
        """
        SELECT column_name, udt_name
        FROM information_schema.columns
        WHERE table_schema = :schema_name
          AND table_name = :table_name
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(query, {"schema_name": schema_name, "table_name": table_name}).fetchall()
    return {row[0]: row[1] for row in rows}


def postgres_cast_type(udt_name: str | None) -> sql.SQL | None:
    """Map udt_name tu information_schema ve type PostgreSQL co the CAST."""
    if not udt_name:
        return None
    type_map = {
        "int2": "smallint",
        "int4": "integer",
        "int8": "bigint",
        "float4": "real",
        "float8": "double precision",
        "numeric": "numeric",
        "bool": "boolean",
        "date": "date",
        "timestamp": "timestamp",
        "timestamptz": "timestamp with time zone",
        "text": "text",
        "varchar": "text",
        "bpchar": "text",
    }
    cast_type = type_map.get(udt_name)
    if cast_type is None:
        return None
    return sql.SQL(cast_type)


def build_staging_select_expression(column: str, target_types: dict[str, str]) -> sql.Composed:
    """Tao bieu thuc SELECT tu staging, cast theo kieu cot bang dich neu can."""
    cast_type = postgres_cast_type(target_types.get(column))
    source_expr = sql.SQL("NULLIF(src.{}::text, '')").format(sql.Identifier(column))
    if cast_type is None or target_types.get(column) in {"text", "varchar", "bpchar"}:
        return sql.SQL("src.{}").format(sql.Identifier(column))
    return sql.SQL("CAST({} AS {})").format(source_expr, cast_type)


def build_staging_compare_expression(column: str, target_types: dict[str, str]) -> sql.Composed:
    """Tao bieu thuc so sanh tu staging co cast ve kieu cot bang dich."""
    return build_staging_select_expression(column, target_types)


def write_temp_cloud_csv(df: pd.DataFrame) -> Path:
    """Ghi tam DataFrame thanh CSV de dung lai COPY PostgreSQL."""
    handle = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    path = Path(handle.name)
    handle.close()
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def upsert_dataframe_to_postgres(
    engine: Engine,
    schema_name: str,
    table_name: str,
    df: pd.DataFrame,
    conflict_cols: str | list[str],
) -> None:
    """Append cac dong chua ton tai vao bang cloud bang staging table."""
    if df.empty:
        print(f"Khong co dong moi de upsert vao {schema_name}.{table_name}.", flush=True)
        return
    if isinstance(conflict_cols, str):
        conflict_cols = [conflict_cols]
    conflict_cols = [col for col in conflict_cols if col in df.columns]
    if not conflict_cols:
        raise ValueError("Thieu cot de so sanh khi append cloud.")

    ensure_schema(engine, schema_name)
    if cloud_table_exists(engine, schema_name, table_name):
        ensure_cloud_columns(engine, schema_name, table_name, list(df.columns))
    temp_table = f"_tmp_{table_name}_incremental"
    temp_path = write_temp_cloud_csv(df)
    try:
        upload_table(engine, schema_name, temp_table, temp_path, if_exists="replace", show_path=False)
        columns = list(df.columns)
        target_types = read_cloud_column_types(engine, schema_name, table_name)

        raw_conn = engine.raw_connection()
        try:
            with raw_conn.cursor() as cursor:
                compare_clause = sql.SQL(" AND ").join(
                    sql.SQL("tgt.{} IS NOT DISTINCT FROM {}").format(
                        sql.Identifier(col),
                        build_staging_compare_expression(col, target_types),
                    )
                    for col in conflict_cols
                )
                insert_sql = sql.SQL(
                    """
                    INSERT INTO {}.{} ({})
                    SELECT {}
                    FROM {}.{} AS src
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM {}.{} AS tgt
                        WHERE {}
                    )
                    """
                ).format(
                    sql.Identifier(schema_name),
                    sql.Identifier(table_name),
                    sql.SQL(", ").join(sql.Identifier(col) for col in columns),
                    sql.SQL(", ").join(build_staging_select_expression(col, target_types) for col in columns),
                    sql.Identifier(schema_name),
                    sql.Identifier(temp_table),
                    sql.Identifier(schema_name),
                    sql.Identifier(table_name),
                    compare_clause,
                )
                cursor.execute(insert_sql)
            raw_conn.commit()
        except Exception:
            raw_conn.rollback()
            raise
        finally:
            raw_conn.close()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP TABLE IF EXISTS "{schema_name}"."{temp_table}"'))
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def get_max_cloud_key(engine: Engine, schema_name: str, table_name: str, key_col: str) -> int:
    """Lay khoa lon nhat hien co tren bang cloud."""
    with engine.connect() as conn:
        value = conn.execute(
            text(f'SELECT COALESCE(MAX("{key_col}"), 0) FROM "{schema_name}"."{table_name}"')
        ).scalar_one()
    return int(value or 0)


def read_cloud_key_map(engine: Engine, schema_name: str, table_name: str, key_col: str, natural_col: str) -> dict:
    """Doc mapping natural key -> surrogate key tu bang dimension tren cloud."""
    query = text(f'SELECT "{natural_col}", "{key_col}" FROM "{schema_name}"."{table_name}"')
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return {row[0]: row[1] for row in rows}


def append_dimension_rows(
    engine: Engine,
    schema_name: str,
    table_name: str,
    dim_df: pd.DataFrame,
    key_col: str,
    natural_col: str,
) -> None:
    """Append cac dong dimension moi theo natural key, giu surrogate key cloud tang dan."""
    if not cloud_table_exists(engine, schema_name, table_name):
        upload_table(engine, schema_name, table_name, MART_DIR / f"{table_name}.csv", if_exists="replace")
        return

    existing_keys = set(read_cloud_key_map(engine, schema_name, table_name, key_col, natural_col))
    new_rows = dim_df.loc[~dim_df[natural_col].isin(existing_keys)].copy()
    if new_rows.empty:
        print(f"Khong co dong dimension moi cho {schema_name}.{table_name}.", flush=True)
        return

    if key_col != natural_col:
        start_key = get_max_cloud_key(engine, schema_name, table_name, key_col)
        new_rows[key_col] = range(start_key + 1, start_key + 1 + len(new_rows))
    upsert_dataframe_to_postgres(engine, schema_name, table_name, new_rows, natural_col)


def build_incremental_dimensions(rows_to_append: pd.DataFrame) -> dict[str, tuple[pd.DataFrame, str, str]]:
    """Tao cac dimension moi tu chinh dong hoa don moi."""
    rows = rows_to_append.copy()
    rows["Ngày chứng từ"] = pd.to_datetime(rows["Ngày chứng từ"], errors="coerce")

    dim_date = rows[["Ngày chứng từ", "Năm", "Tháng", "Quý", "Năm-Tháng"]].drop_duplicates().copy()
    dim_date["date_key"] = dim_date["Ngày chứng từ"].dt.strftime("%Y%m%d").astype("Int64")
    dim_date["Tên tháng"] = "Tháng " + dim_date["Tháng"].astype("Int64").astype(str)
    dim_date = dim_date[["date_key", "Ngày chứng từ", "Năm", "Quý", "Tháng", "Tên tháng", "Năm-Tháng"]]

    dim_customer = rows[["Mã khách hàng", "Tên khách hàng", "Nhóm khách hàng"]].drop_duplicates("Mã khách hàng").copy()
    dim_product = rows[
        ["Mã sản phẩm", "Tên sản phẩm", "Nhóm sản phẩm", "Loại sản phẩm"]
    ].drop_duplicates("Mã sản phẩm").copy()
    dim_channel = rows[["Kênh"]].drop_duplicates("Kênh").copy()

    return {
        "dim_date": (dim_date, "date_key", "date_key"),
        "dim_customer": (dim_customer, "customer_key", "Mã khách hàng"),
        "dim_product": (dim_product, "product_key", "Mã sản phẩm"),
        "dim_channel": (dim_channel, "channel_key", "Kênh"),
    }


def build_incremental_fact(engine: Engine, rows_to_append: pd.DataFrame) -> pd.DataFrame:
    """Tao fact_sales moi bang cach map natural key sang surrogate key dang co tren cloud."""
    rows = rows_to_append.copy()
    rows["Ngày chứng từ"] = pd.to_datetime(rows["Ngày chứng từ"], errors="coerce")
    rows["date_key"] = rows["Ngày chứng từ"].dt.strftime("%Y%m%d").astype("Int64")

    customer_map = read_cloud_key_map(engine, "dw", "dim_customer", "customer_key", "Mã khách hàng")
    product_map = read_cloud_key_map(engine, "dw", "dim_product", "product_key", "Mã sản phẩm")
    channel_map = read_cloud_key_map(engine, "dw", "dim_channel", "channel_key", "Kênh")

    fact = pd.DataFrame(
        {
            "date_key": rows["date_key"],
            "customer_key": rows["Mã khách hàng"].map(customer_map),
            "product_key": rows["Mã sản phẩm"].map(product_map),
            "channel_key": rows["Kênh"].map(channel_map),
            "Số chứng từ": rows["Số chứng từ"],
            "ĐVT": rows["ĐVT"],
            "Số lượng": rows["Số lượng"],
            "Khối lượng KG": rows["Khối lượng KG"],
            "Đơn giá": rows["Đơn giá"],
            "Doanh số": rows["Doanh số"],
            "Chiết khấu": rows["Chiết khấu"],
            "Doanh thu thuần": rows["Doanh thu thuần"],
            "Số lượng trả lại": rows["Số lượng trả lại"],
            "Giá trị trả lại": rows["Giá trị trả lại"],
            "Giá vốn đơn vị": rows["Giá vốn đơn vị"],
            "Tổng giá vốn": rows["Tổng giá vốn"],
            "Lợi nhuận": rows["Lợi nhuận"],
            "Biên lợi nhuận": rows["Biên lợi nhuận"],
            "Tỷ lệ chiết khấu": rows["Tỷ lệ chiết khấu"],
            "Tỷ lệ hoàn trả": rows["Tỷ lệ hoàn trả"],
            "Trả hàng": rows["Trả hàng"],
            "Giai đoạn": rows["Giai đoạn"],
            "Nguồn dữ liệu": rows["Nguồn dữ liệu"],
            "Chi nhánh": rows["Chi nhánh"],
            "Vùng doanh thu": rows["Vùng doanh thu"],
        }
    )
    start_key = get_max_cloud_key(engine, "dw", "fact_sales", "sales_id")
    fact.insert(0, "sales_id", range(start_key + 1, start_key + 1 + len(fact)))
    return fact


def upload_incremental_cloud(rows_to_append: pd.DataFrame) -> None:
    """Dong bo cloud theo kieu incremental: append fact/dim, replace mart tong hop."""
    engine = create_cloud_engine()
    try:
        check_cloud_connection(engine)
        rows_to_append = rows_to_append.copy()
        if rows_to_append.empty:
            print("Khong co dong pending can dong bo cloud.", flush=True)
            return

        print("Dang append dimension moi vao dw.dim_*...", flush=True)
        for table_name, (dim_df, key_col, natural_col) in build_incremental_dimensions(rows_to_append).items():
            append_dimension_rows(engine, "dw", table_name, dim_df, key_col, natural_col)

        fact_schema, fact_path = SUMMARY_CLOUD_TABLES["fact_sales"]
        if not cloud_table_exists(engine, fact_schema, "fact_sales"):
            print("Bang dw.fact_sales chua ton tai. Upload full fact_sales mot lan.", flush=True)
            upload_table(engine, fact_schema, "fact_sales", fact_path, if_exists="replace")

        print("Dang append dong fact moi vao dw.fact_sales...", flush=True)
        fact_rows = build_incremental_fact(engine, rows_to_append)
        fact_compare_cols = [col for col in fact_rows.columns if col != "sales_id"]
        upsert_dataframe_to_postgres(engine, "dw", "fact_sales", fact_rows, fact_compare_cols)

        print("Dang replace cac bang mart tong hop sau khi local da rebuild...", flush=True)
        for table_name, (schema_name, path) in SUMMARY_CLOUD_TABLES.items():
            if schema_name != "mart":
                continue
            print(f"Dang upload {schema_name}.{table_name}...", flush=True)
            upload_table(engine, schema_name, table_name, path, if_exists="replace")
        print("Hoan tat incremental upload len Supabase.", flush=True)
    finally:
        engine.dispose()


def upload_ai_update_insight(insight_df: pd.DataFrame) -> None:
    """Append bang thong bao AI Agent len Supabase schema ai."""
    if insight_df.empty:
        print("Khong co insight AI Agent de upload.", flush=True)
        return

    engine = create_cloud_engine()
    try:
        check_cloud_connection(engine)
        schema_name = "ai"
        table_name = "update_insight"
        ensure_schema(engine, schema_name)

        temp_path = write_temp_cloud_csv(insight_df)
        try:
            if not cloud_table_exists(engine, schema_name, table_name):
                upload_table(engine, schema_name, table_name, temp_path, if_exists="replace")
            else:
                upsert_dataframe_to_postgres(engine, schema_name, table_name, insight_df, "update_id")
        finally:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass
        print("Da upload AI Agent insight len ai.update_insight.", flush=True)
    finally:
        engine.dispose()


def reset_ai_update_insight_table(engine: Engine | None = None) -> None:
    """Replace ai.update_insight bang bang rong co du cot khi chay lai full upload."""
    owns_engine = engine is None
    engine = engine or create_cloud_engine()
    try:
        if owns_engine:
            check_cloud_connection(engine)
        ensure_schema(engine, "ai")
        empty_insight = pd.DataFrame(columns=UPDATE_INSIGHT_COLUMNS)
        empty_insight.to_sql(
            "update_insight",
            engine,
            schema="ai",
            if_exists="replace",
            index=False,
            dtype=AI_UPDATE_INSIGHT_DTYPE,
        )
        print("Da reset bang ai.update_insight ve rong va giu day du cot.", flush=True)
    finally:
        if owns_engine:
            engine.dispose()


def replace_ai_update_insight_table() -> None:
    """Giu tuong thich ten ham cu: reset bang ai.update_insight ve rong."""
    reset_ai_update_insight_table()

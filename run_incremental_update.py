import argparse
import site
import sys
from pathlib import Path


USER_SITE = site.getusersitepackages()
try:
    if Path(USER_SITE).exists() and USER_SITE not in sys.path:
        sys.path.insert(0, USER_SITE)
except PermissionError:
    pass

PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.incremental_update import DEFAULT_NEW_ORDERS_FILE, run_incremental_update, upload_pending_cloud


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cap nhat hoa don moi theo luong Incremental ETL, khong anh huong pipeline full load."
    )
    parser.add_argument(
        "new_orders",
        nargs="?",
        default=str(DEFAULT_NEW_ORDERS_FILE),
        help="Duong dan file hoa don moi (.csv, .xlsx, .xls). Mac dinh: data/raw/new_orders.csv",
    )
    parser.add_argument(
        "--upload-cloud",
        action="store_true",
        help="Upload cac dong pending len Supabase: append dw.dim_*, dw.fact_sales va replace mart_*.",
    )
    parser.add_argument(
        "--ai-agent",
        action="store_true",
        help="Sinh thong bao AI Agent sau lan cap nhat va upload len Supabase neu co --upload-cloud.",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Gui email thong bao sau khi AI Agent sinh insight. Can dung kem --ai-agent.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    result = run_incremental_update(args.new_orders, upload_cloud=False)
    report = result["report"]

    print("Incremental ETL da chay xong.")
    print(f"File hoa don moi: {args.new_orders}")
    print(f"So dong dau vao: {report['raw_new_rows']:,}")
    print(f"Trung voi du lieu da co: {report['duplicate_with_existing_rows']:,}")
    print(f"Trung trong file moi: {report['duplicate_inside_new_file_rows']:,}")
    print(f"So dong append vao sales_final: {report['appended_rows']:,}")
    print("Bang local da cap nhat: data/clean/sales_final.csv va data/mart/*.csv")

    uploaded_cloud = False
    if args.upload_cloud:
        print("Bat dau dong bo Supabase...")
        uploaded_cloud = upload_pending_cloud(result)

    if args.ai_agent and report["appended_rows"] > 0:
        from src.ai_agent import append_ai_update_insight, build_ai_update_insight

        print("Dang sinh AI Agent insight...")
        insight_df = build_ai_update_insight(
            before_sales=result["sales_before_update"],
            after_sales=result["updated_sales"],
            report=report,
            new_orders_path=args.new_orders,
            uploaded_cloud=uploaded_cloud,
            use_llm=True,
        )
        insight_path = append_ai_update_insight(insight_df)
        print(f"Da luu AI Agent insight: {insight_path}")
        if args.upload_cloud:
            from src.cloud_upload import upload_ai_update_insight

            upload_ai_update_insight(insight_df)
        if args.send_email:
            from src.email_notification import notify_update_insight

            email_result = notify_update_insight(insight_df)
            if email_result.get("sent"):
                print(f"Da gui email thong bao toi: {', '.join(email_result['recipients'])}")
            elif email_result.get("error"):
                print(f"Gui email that bai: {email_result['error']}")
            else:
                print(f"Bo qua gui email: {email_result.get('reason', 'khong du dieu kien')}")
    elif args.ai_agent:
        print("Bo qua AI Agent insight vi khong co dong hoa don moi duoc append.")
    elif args.send_email:
        print("Bo qua gui email vi can bat --ai-agent de co noi dung insight.")

    if uploaded_cloud:
        print("Da dong bo Supabase: append dw.dim_*, dw.fact_sales; replace mart_*; lam rong file pending cloud.")
    elif args.upload_cloud and report["appended_rows"] == 0:
        print("Khong co dong pending de dong bo cloud.")
    else:
        print("Chua upload cloud. Chay them --upload-cloud neu can dong bo Supabase.")

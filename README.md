# DATN - PHÂN TÍCH HIỆU QUẢ TÁI CẤU TRÚC VÀ TÌNH HÌNH KINH DOANH CỦA DOANH NGHIỆP CÀ PHÊ

Dự án xây dựng hệ thống xử lý, phân tích và trực quan hóa dữ liệu bán hàng cà phê. Luồng chính bắt đầu từ dữ liệu Excel gốc, thực hiện ETL bằng Python, tạo dữ liệu sạch, xây dựng Data Mart, huấn luyện mô hình dự báo doanh thu, đồng bộ dữ liệu lên Supabase và phục vụ dashboard Tableau.

Ngoài luồng xử lý ban đầu, dự án có thêm luồng mở rộng để cập nhật hóa đơn mới theo cơ chế incremental ETL, sinh AI Insight đánh giá tác động KPI sau mỗi lần cập nhật và gửi email thông báo khi cần.

## 1. Mục tiêu

- Chuẩn hóa dữ liệu bán hàng từ nhiều nguồn Excel.
- Hợp nhất dữ liệu bán hàng giai đoạn 2023-2026.
- Xây dựng bảng dữ liệu sạch `sales_final.csv` làm nguồn dữ liệu trung tâm.
- Xây dựng Data Mart theo mô hình star schema và các bảng tổng hợp phục vụ dashboard.
- Dự báo doanh thu năm 2026 và so sánh kết quả dự báo với thực tế.
- Upload dữ liệu lên Supabase PostgreSQL để Tableau có thể kết nối trực tiếp.
- Bổ sung luồng cập nhật hóa đơn mới, cảnh báo KPI và AI Insight tự động.

## 2. Kiến trúc tổng quan

```text
Raw Excel Data
    -> Python ETL
    -> Staging Data
    -> Clean Data Final
    -> Data Mart
    -> Forecast Model
    -> Supabase Cloud Database
    -> Tableau Dashboard
    -> Analytical Report
```

Luồng mở rộng:

```text
New Orders Data
    -> Incremental ETL
    -> Append sales_final local
    -> Rebuild Data Mart local
    -> Optional AI Business Analyst Agent
    -> Optional Supabase Sync
    -> Optional Email Notification
    -> Tableau Dashboard
```

## 3. Cấu trúc thư mục

```text
DuAnTotNghiep/
├── data/
│   ├── raw/              # File Excel/CSV đầu vào
│   ├── staging/          # Dữ liệu trung gian sau extract/clean từng nguồn
│   ├── clean/            # Dữ liệu sạch hợp nhất
│   ├── mart/             # Star schema và aggregate mart
│   ├── model/            # Dữ liệu và kết quả mô hình dự báo
│   └── ai_agent/         # Kết quả AI Insight local
├── notebooks/            # Notebook theo từng giai đoạn xử lý
├── outputs/              # Báo cáo, hình ảnh, file Excel kết quả
├── src/                  # Source code chính
├── run_pipeline.py       # Chạy toàn bộ luồng chính local
├── upload_to_cloud.py    # Upload dữ liệu local lên Supabase
├── run_incremental_update.py
├── requirements.txt
└── README.md
```

## 4. Dữ liệu đầu vào

Các file dữ liệu gốc được đặt trong `data/raw`:

| File | Vai trò |
|---|---|
| `Data_2023-2025.xlsx` | Dữ liệu bán hàng lịch sử trước tái cấu trúc |
| `Data_Sales du an.xlsx` | Dữ liệu bán hàng năm 2026 |
| `Giá vốn theo sp.xlsx` | Bảng giá vốn theo sản phẩm |
| `new_orders.csv` | Hóa đơn mới dùng cho luồng incremental update |

Lưu ý: dữ liệu gốc trong `data/raw` được xem là dữ liệu nguồn, không chỉnh sửa trực tiếp trong quá trình xử lý.

## 5. Luồng chính

Luồng chính là full ETL, dùng để chạy lại toàn bộ dự án từ dữ liệu gốc.

```text
Extract
    -> Transform / Cleaning
    -> Build Clean Final
    -> Build Data Mart
    -> Forecast Revenue
    -> Export Excel
    -> Optional Upload Supabase
```

### 5.1 Extract

Module `src/extract.py` đọc dữ liệu từ các file Excel trong `data/raw`, chuẩn hóa tên cột và đưa dữ liệu thô vào `data/staging`.

### 5.2 Transform và làm sạch dữ liệu

Module `src/transform.py` thực hiện:

- Chuẩn hóa kiểu dữ liệu ngày, số và text.
- Chuẩn hóa các nhóm phân loại như khách hàng, sản phẩm, kênh bán hàng.
- Merge dữ liệu giá vốn cho dữ liệu 2026.
- Xử lý các giá trị thiếu theo ý nghĩa nghiệp vụ.
- Tạo các chỉ số như doanh thu thuần, lợi nhuận, biên lợi nhuận, tỷ lệ chiết khấu và tỷ lệ hoàn trả.

Kết quả chính:

```text
data/clean/sales_final.csv
data/clean/data_quality_overview.csv
```

### 5.3 Data Mart

Module `src/mart.py` xây dựng Data Mart từ `sales_final.csv`.

Nhóm star schema:

```text
dim_date.csv
dim_customer.csv
dim_product.csv
dim_channel.csv
fact_sales.csv
```

Nhóm aggregate mart:

```text
mart_overview_year.csv
mart_time_month.csv
mart_time_quarter.csv
mart_channel.csv
mart_product_group.csv
mart_region.csv
mart_customer_group.csv
mart_channel_product.csv
mart_quarter_channel.csv
mart_pareto_customer_group.csv
forecast_vs_actual.csv
```

Các bảng mart được dùng làm nguồn chính cho phân tích, Tableau và báo cáo.

### 5.4 Mô hình dự báo

Module `src/modeling.py` xây dựng dữ liệu theo tháng, tạo feature thời gian, backtest mô hình và dự báo doanh thu tháng 1-5/2026.

Kết quả được lưu tại:

```text
data/model/
data/mart/forecast_vs_actual.csv
```

### 5.5 Xuất kết quả

Pipeline xuất file Excel tổng hợp tại:

```text
outputs/excel/Ket_qua_phan_tich_du_bao_pipeline.xlsx
```

## 6. Luồng mở rộng Incremental Update

Luồng mở rộng dùng khi hệ thống đã có dữ liệu ban đầu và cần cập nhật thêm hóa đơn mới.

Nguồn đầu vào mặc định:

```text
data/raw/new_orders.csv
```

Quy trình:

```text
Đọc dữ liệu hiện tại
    -> Lưu snapshot trước cập nhật trong RAM
    -> Đọc file hóa đơn mới
    -> Làm sạch và chuẩn hóa theo schema 2026
    -> Kiểm tra trùng theo toàn bộ dòng giao dịch
    -> Append dòng mới vào sales_final local
    -> Rebuild toàn bộ Data Mart local
    -> Lưu pending rows nếu chưa upload cloud
    -> Optional upload Supabase
    -> Optional sinh AI Insight
    -> Optional gửi email thông báo
```

Điểm quan trọng:

- Không kiểm tra trùng chỉ theo mã chứng từ, vì một chứng từ có thể có nhiều dòng sản phẩm.
- Các dòng mới hợp lệ được append vào `sales_final.csv`.
- Data Mart được rebuild lại toàn bộ để các bảng tổng hợp luôn chính xác.
- Nếu chạy local nhưng chưa upload cloud, dữ liệu mới được lưu trong `pending_cloud_sales_final.csv`.
- Khi chạy lại với `--upload-cloud`, hệ thống upload toàn bộ các dòng pending trước đó, sau đó mới làm rỗng file pending nếu upload thành công.

## 7. AI Business Analyst Agent

AI Agent không dùng để dự báo doanh thu. Vai trò của AI Agent là đánh giá tác động sau khi có hóa đơn mới.

AI Agent thực hiện:

- So sánh KPI trước và sau cập nhật.
- Đánh giá trạng thái `positive`, `negative` hoặc `neutral`.
- Đánh giá mức độ `low`, `medium` hoặc `high`.
- Sinh insight bằng ngôn ngữ tự nhiên.
- Gợi ý hành động theo dõi.
- Lưu kết quả để Tableau trực quan thành trang cảnh báo.

Kết quả local:

```text
data/ai_agent/update_insight.csv
```

Kết quả cloud:

```text
ai.update_insight
```

AI Insight chỉ được sinh khi có dòng hóa đơn mới được append thành công.

## 8. Email Notification

Luồng email là phần mở rộng tùy chọn, dùng để gửi thông báo sau khi AI Agent sinh insight.

Email bao gồm:

- Thời gian cập nhật.
- Trạng thái và mức độ cảnh báo.
- Số dòng hóa đơn mới.
- Bảng so sánh KPI trước và sau cập nhật.
- Nội dung AI Insight.
- Khuyến nghị theo dõi.

Email chỉ chạy khi dùng tùy chọn:

```powershell
python run_incremental_update.py --ai-agent --send-email
```

Nếu muốn vừa cập nhật cloud vừa gửi email:

```powershell
python run_incremental_update.py --upload-cloud --ai-agent --send-email
```

## 9. Supabase Cloud

Dữ liệu local có thể được upload lên Supabase PostgreSQL để Tableau kết nối.

Các schema sử dụng:

| Schema | Nội dung |
|---|---|
| `audit` | Bảng kiểm tra chất lượng dữ liệu |
| `dw` | Bảng dimension và fact |
| `mart` | Bảng aggregate mart và forecast comparison |
| `model` | Bảng dữ liệu mô hình dự báo |
| `ai` | Bảng AI Insight |
| `clean` | Bảng clean lớn nếu bật upload bảng lớn |

Luồng full upload:

```text
Local CSV
    -> Supabase PostgreSQL
    -> Tableau Live/Extract Connection
```

Luồng incremental upload:

```text
Append dw.dim_*
Append dw.fact_sales
Replace mart.*
Upload ai.update_insight nếu bật AI Agent
```

## 10. Notebook

Các notebook chính:

| Notebook | Nội dung |
|---|---|
| `01_lam_sach_du_lieu.ipynb` | Làm sạch và chuẩn hóa dữ liệu |
| `02_xay_dung_data_mart.ipynb` | Xây dựng Data Mart |
| `03_eda_dac_diem_du_lieu.ipynb` | EDA đặc điểm dữ liệu |
| `03_eda_insight.ipynb` | EDA theo hướng phân tích insight |
| `04_du_bao_ml.ipynb` | Mô hình dự báo doanh thu |
| `05_xuat_tableau.ipynb` | Chuẩn bị dữ liệu phục vụ Tableau |

## 11. Cài đặt

Yêu cầu:

- Python 3.10 trở lên
- pip
- Jupyter Notebook nếu muốn chạy notebook
- Tài khoản Supabase nếu cần upload cloud
- Tableau Desktop/Public/Cloud nếu cần trực quan hóa

Cài thư viện:

```powershell
pip install -r requirements.txt
```

## 12. Cấu hình môi trường

Tạo file `.env` ở thư mục gốc dự án nếu cần dùng AI Agent hoặc email.

Ví dụ:

```env
GEMINI_API_KEY=your_gemini_api_key
AI_AGENT_MODEL=gemini-3-flash-preview

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_TO=receiver1@gmail.com,receiver2@gmail.com
EMAIL_CC=
EMAIL_SEND_MIN_SEVERITY=low
EMAIL_SEND_NEGATIVE_ONLY=false
```

Không commit file `.env` lên GitHub.

## 13. Cách chạy

Chạy toàn bộ luồng chính local:

```powershell
python run_pipeline.py
```

Upload dữ liệu local lên Supabase:

```powershell
python upload_to_cloud.py
```

Chạy cập nhật hóa đơn mới local:

```powershell
python run_incremental_update.py
```

Chạy cập nhật hóa đơn mới và upload Supabase:

```powershell
python run_incremental_update.py --upload-cloud
```

Chạy cập nhật hóa đơn mới, sinh AI Insight và upload Supabase:

```powershell
python run_incremental_update.py --upload-cloud --ai-agent
```

Chạy cập nhật hóa đơn mới, sinh AI Insight, upload Supabase và gửi email:

```powershell
python run_incremental_update.py --upload-cloud --ai-agent --send-email
```

Chạy với file hóa đơn mới khác:

```powershell
python run_incremental_update.py path/to/new_orders.csv --upload-cloud --ai-agent
```

## 14. Vai trò các module

| File | Vai trò |
|---|---|
| `src/config.py` | Quản lý đường dẫn và thư mục dự án |
| `src/extract.py` | Đọc dữ liệu từ Excel |
| `src/transform.py` | Làm sạch, chuẩn hóa và hợp nhất dữ liệu |
| `src/mart.py` | Xây dựng star schema và aggregate mart |
| `src/modeling.py` | Xây dựng mô hình dự báo doanh thu |
| `src/pipeline.py` | Điều phối luồng chính |
| `src/cloud_upload.py` | Upload dữ liệu lên Supabase |
| `src/incremental_update.py` | Xử lý hóa đơn mới theo incremental ETL |
| `src/ai_agent.py` | Sinh AI Insight sau cập nhật |
| `src/email_notification.py` | Gửi email cảnh báo |
| `src/utils.py` | Các hàm tiện ích dùng chung |

## 15. Kết quả đầu ra chính

| Đầu ra | Vị trí |
|---|---|
| Dữ liệu sạch hợp nhất | `data/clean/sales_final.csv` |
| Data Mart | `data/mart/*.csv` |
| Kết quả mô hình dự báo | `data/model/*.csv` |
| So sánh dự báo và thực tế | `data/mart/forecast_vs_actual.csv` |
| AI Insight | `data/ai_agent/update_insight.csv` |
| Excel tổng hợp | `outputs/excel/Ket_qua_phan_tich_du_bao_pipeline.xlsx` |
| Báo cáo Markdown | `outputs/*.md` |

## 16. Ghi chú Tableau

Tableau có thể kết nối Supabase theo hai cách:

- Live connection: đọc trực tiếp dữ liệu từ Supabase khi dashboard phát sinh query.
- Extract: lưu bản sao dữ liệu trong Tableau và cần refresh extract để cập nhật dữ liệu mới.

Với trang AI Insight, nên dùng live connection kết hợp auto refresh để dashboard tự cập nhật gần realtime sau mỗi lần chạy luồng incremental update.

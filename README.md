# DuAnTotNghiep - Phan tich kinh doanh cafe

## Kien truc quy trinh

Quy trinh du lieu duoc to chuc theo thu tu:

```text
data/raw
  -> data/staging
  -> data/clean
  -> data/mart
  -> notebooks / Tableau
```

Trong do:

- `data/raw`: chua file goc, khong sua tay trong pipeline.
- `data/staging`: chua raw da doc lai va cac bang clean rieng tung nguon.
- `data/clean`: chua `sales_final.csv`, day la data clean hop nhat 2023-2026.
- `data/mart`: chua fact/dim va aggregate mart cho Tableau.
- `data/model`: chua bang trung gian, backtest va metric cua mo hinh du bao.
- `src`: chua ham Python tai su dung.
- `notebooks`: chua cac file ipynb theo tung giai doan trinh bay.

## File dau vao

Tat ca file nguon duoc dua vao `data/raw`:

```text
data/raw/Data_2023-2025.xlsx
data/raw/Data_Sales du an.xlsx
data/raw/Giá vốn theo sp.xlsx
```

## Thu tu chay notebook

```text
01_lam_sach_du_lieu.ipynb
02_xay_dung_data_mart.ipynb
03_eda.ipynb
04_du_bao_ml.ipynb
05_xuat_tableau.ipynb
```

## Chay nhanh toan bo pipeline

```powershell
python run_pipeline.py
```

Lenh tren se chay:

```text
cleaning -> data mart -> revenue forecast -> Excel export
```

## Vai tro cac module Python

- `src/config.py`: cau hinh duong dan va thu muc.
- `src/extract.py`: doc Excel dau vao.
- `src/transform.py`: lam sach 2023-2025, 2026, gia von; merge gia von vao 2026; tao `sales_final`.
- `src/mart.py`: tao fact/dim va cac aggregate mart.
- `src/modeling.py`: tao monthly model data, backtest va du bao doanh thu T1-T5/2026.
- `src/pipeline.py`: ket noi cac stage thanh quy trinh hoan chinh.
- `src/utils.py`: ham phu tro chuan hoa text, so, xuat CSV

## Bang clean quan trong

```text
data/clean/sales_final.csv
data/clean/data_quality_overview.csv
```

## Cac mart Tableau quan trong

- `fact_sales.csv`
- `dim_date.csv`
- `dim_customer.csv`
- `dim_product.csv`
- `dim_channel.csv`
- `mart_overview_year.csv`
- `mart_time_month.csv`
- `mart_time_quarter.csv`
- `mart_channel.csv`
- `mart_product_group.csv`
- `mart_channel_product.csv`
- `mart_quarter_channel.csv`
- `mart_region.csv`
- `mart_customer_group.csv`
- `mart_pareto_customer_group.csv`
- `forecast_vs_actual.csv`

## Bang model/intermediate

Cac file nay nam trong `data/model`, khong can ket noi Tableau neu chi lam dashboard:

- `monthly_model_base.csv`
- `monthly_model_data.csv`
- `model_revenue_metrics.csv`
- `backtest_revenue.csv`
- `forecast_revenue_2026.csv`

## Ghi chu nghiep vu

Loi nhuan 2026 duoc tinh bang:

```text
Loi nhuan 2026 = Doanh thu thuan - Tong gia von
Tong gia von = Gia von don vi * Tong so luong ban
```

Cong thuc nay dua tren file `Giá vốn theo sp.xlsx`, merge theo `Mã sản phẩm`.

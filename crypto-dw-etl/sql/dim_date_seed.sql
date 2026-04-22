-- ====================================================================
-- Script: dim_date_seed.sql
-- Mục đích: Sinh dữ liệu tự động cho bảng gold.dim_date (Từ 2023 đến 2025)
-- Dialect: PostgreSQL (Postgres 15)
-- Lưu ý: Chạy script này SAU KHI đã tạo bảng bằng 02_gold_ddl.sql
-- ====================================================================

-- Xóa dữ liệu cũ (nếu có) để tránh duplicate khi chạy lại
TRUNCATE TABLE gold.dim_date RESTART IDENTITY CASCADE;

-- Sinh chuỗi liên tục từng ngày sử dụng hàm generate_series của Postgres
INSERT INTO gold.dim_date (
    date_id, 
    full_date, 
    day, 
    week, 
    month, 
    quarter, 
    year, 
    day_of_week, 
    is_weekend
)
SELECT
    -- Tạo date_id chuẩn định dạng YYYYMMDD (INT)
    CAST(TO_CHAR(d, 'YYYYMMDD') AS INT)         AS date_id,
    
    -- Ngày gốc
    d::date                                     AS full_date,
    
    -- Trích xuất các thành phần phân tích
    CAST(EXTRACT(DAY FROM d) AS SMALLINT)       AS day,
    CAST(EXTRACT(WEEK FROM d) AS SMALLINT)      AS week,
    CAST(EXTRACT(MONTH FROM d) AS SMALLINT)     AS month,
    CAST(EXTRACT(QUARTER FROM d) AS SMALLINT)   AS quarter,
    CAST(EXTRACT(YEAR FROM d) AS SMALLINT)      AS year,
    
    -- Lấy tên thứ trong tuần (VD: 'Mon', 'Tue')
    TO_CHAR(d, 'Dy')                            AS day_of_week,
    
    -- ISODOW = 6 là Thứ 7, ISODOW = 7 là Chủ Nhật
    CASE 
        WHEN EXTRACT(ISODOW FROM d) IN (6, 7) THEN TRUE 
        ELSE FALSE 
    END                                         AS is_weekend
FROM generate_series(
    '2023-01-01'::timestamp, 
    '2025-12-31'::timestamp, 
    '1 day'::interval
) d;

-- Kiểm tra kết quả (Optional)
-- SELECT * FROM gold.dim_date ORDER BY date_id LIMIT 10;

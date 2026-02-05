-- 添加发票分类和抵扣字段
-- 迁移时间: 2026-01-28 12:00:07

-- 添加发票大类字段
ALTER TABLE material_invoice 
ADD COLUMN invoice_category VARCHAR(64) NULL COMMENT '发票大类';

-- 添加可否抵扣字段
ALTER TABLE material_invoice 
ADD COLUMN deductible VARCHAR(64) NULL COMMENT '可否抵扣';

-- 验证字段已添加
SELECT COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'material_invoice' 
AND COLUMN_NAME IN ('invoice_category', 'deductible');

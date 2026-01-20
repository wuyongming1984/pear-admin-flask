-- 导出数据: nursery_plant
USE pear_admin;
DROP TABLE IF EXISTS nursery_plant;

CREATE TABLE `nursery_plant` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL COMMENT '苗木名称',
  `category` VARCHAR(50) COMMENT '分类',
  `spec` VARCHAR(100) COMMENT '规格',
  `unit` VARCHAR(20) COMMENT '单位',
  `quantity` DECIMAL(10, 2) DEFAULT 0 COMMENT '当前库存数量',
  `price` DECIMAL(10, 2) DEFAULT 0 COMMENT '加权平均成本价',
  `location` VARCHAR(100) COMMENT '存放位置',
  `remark` VARCHAR(255) COMMENT '备注',
  `create_at` DATETIME DEFAULT NULL COMMENT '创建时间',
  `update_at` DATETIME DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `nursery_plant` (`id`, `name`, `category`, `spec`, `unit`, `quantity`, `price`, `location`, `remark`, `create_at`, `update_at`) VALUES (1, '香樟', '苗木', '15-18', '株', 42, 500, '东', '', '2026-01-19 21:00:51.015076', '2026-01-19 21:02:05.359454');
INSERT INTO `nursery_plant` (`id`, `name`, `category`, `spec`, `unit`, `quantity`, `price`, `location`, `remark`, `create_at`, `update_at`) VALUES (2, '香樟', '苗木', '25', '株', 201, 500.50248756218906, '南01', '', '2026-01-19 21:39:33.127729', '2026-01-20 01:50:47.176609');
INSERT INTO `nursery_plant` (`id`, `name`, `category`, `spec`, `unit`, `quantity`, `price`, `location`, `remark`, `create_at`, `update_at`) VALUES (3, '桂花', '苗木', 'p100', '盆', 175, 506.5050285714286, '西02', '', '2026-01-19 21:39:33.384269', '2026-01-20 01:50:47.748077');
INSERT INTO `nursery_plant` (`id`, `name`, `category`, `spec`, `unit`, `quantity`, `price`, `location`, `remark`, `create_at`, `update_at`) VALUES (4, '桂花', '苗木', 'p300', '株', 100, 504.5049504950495, '东01', '', '2026-01-19 21:39:33.155766', '2026-01-20 01:50:47.203519');
INSERT INTO `nursery_plant` (`id`, `name`, `category`, `spec`, `unit`, `quantity`, `price`, `location`, `remark`, `create_at`, `update_at`) VALUES (5, '鸡', '养殖', '1斤', '只', 96, 508, '西02', '', '2026-01-19 21:39:33.918948', '2026-01-20 01:50:48.086352');
INSERT INTO `nursery_plant` (`id`, `name`, `category`, `spec`, `unit`, `quantity`, `price`, `location`, `remark`, `create_at`, `update_at`) VALUES (6, '鸭', '养殖', '统货', '只', 10, 509, '西02', '', '2026-01-19 21:39:34.195710', '2026-01-20 01:50:48.332530');
INSERT INTO `nursery_plant` (`id`, `name`, `category`, `spec`, `unit`, `quantity`, `price`, `location`, `remark`, `create_at`, `update_at`) VALUES (7, '青菜', '蔬菜', '统货', '斤', 20, 510, '西02', '', '2026-01-19 21:39:34.440854', '2026-01-20 01:50:48.620383');
INSERT INTO `nursery_plant` (`id`, `name`, `category`, `spec`, `unit`, `quantity`, `price`, `location`, `remark`, `create_at`, `update_at`) VALUES (8, '香樟', '苗木', '25', '株', 101, 501, '南01', '', '2026-01-19 21:39:33.134725', '2026-01-19 21:39:33.134725');
INSERT INTO `nursery_plant` (`id`, `name`, `category`, `spec`, `unit`, `quantity`, `price`, `location`, `remark`, `create_at`, `update_at`) VALUES (9, '香樟', '苗木', '18', '株', 206, 503, '北03', '', '2026-01-19 21:39:33.155766', '2026-01-20 01:50:47.204041');
INSERT INTO `nursery_plant` (`id`, `name`, `category`, `spec`, `unit`, `quantity`, `price`, `location`, `remark`, `create_at`, `update_at`) VALUES (10, '桂花', '苗木', 'p300', '株', 46, 505, '东01', '', '2026-01-19 21:39:33.156765', '2026-01-19 22:39:38.619282');
INSERT INTO `nursery_plant` (`id`, `name`, `category`, `spec`, `unit`, `quantity`, `price`, `location`, `remark`, `create_at`, `update_at`) VALUES (11, '香樟', '苗木', '20', '株', 195, 502, '西02', '', '2026-01-19 21:39:33.156765', '2026-01-20 01:50:47.203519');

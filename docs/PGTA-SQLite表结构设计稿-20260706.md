# PGTA SQLite 表结构设计稿

## 目标

先为 `PGTA` 设计一张可承接 `2023下半年 / 2024 / 2025 / 2026` 静态快照的 SQLite 平表。

当前目标不是做长期统一模型，而是：

1. 先把静态数据源整合准确
2. 优先保证当前底层统计函数依赖字段可稳定映射
3. 为后续从 Excel 切换到 SQLite 执行层做准备

约束：

- 不追求和未来实时 API 字段完全一致
- 不要求库表字段名严格贴 Excel 原列名
- 只要字段语义稳定、可追溯、可正确支持当前统计即可

---

## 数据来源

本表整合以下来源：

1. [PGTA胚胎统计表-2023年.xlsx](/home/zhangly/repo/github/yk-hospital-data-review-agent/docs/PGTA胚胎统计表-2023年.xlsx)
   - `7月-12月`
2. [PGTA数据统计输出-2024.xlsx](/home/zhangly/repo/github/yk-hospital-data-review-agent/docs/PGTA数据统计输出-2024.xlsx)
   - `源数据`
3. [PGTA数据统计输出-2025年.xlsx](/home/zhangly/repo/github/yk-hospital-data-review-agent/docs/PGTA数据统计输出-2025年.xlsx)
   - `2025年-数据`
4. [PGTA数据统计输出-2026.6.30.xlsx](/home/zhangly/repo/github/yk-hospital-data-review-agent/docs/PGTA数据统计输出-2026.6.30.xlsx)
   - `2026年-数据`

说明：

- `2024 / 2025 / 2026` 基本可视为同代结构
- `2023年7-12月` 已接近同代结构
- `2023年1-6月` 是更老的一代格式，当前不纳入 SQLite 导入范围

---

## 表名

建议主表名：

`pgta_snapshot_raw`

这个名字强调两点：

1. 它承接的是 `PGTA` 静态快照
2. 它是“原始快照的可执行落地表”，不是最终统一业务模型

---

## 设计原则

1. 以 `2025年-数据` 为主参考结构
2. 对 `2024 / 2026 / 2023` 做列名映射兼容
3. 当前底层函数依赖字段优先保证准确
4. 映射不到的字段允许为空
5. 导入时保留来源信息，便于回溯

---

## 当前必须优先保证的字段

以下字段是当前 `PGT-A` 执行链路优先要保证准确映射的字段。

直接对应当前代码实际使用：

- `month_bucket`
- `report_review_time`
- `sample_id`
- `hospital_name`
- `sample_type`
- `order_id`
- `sample_name`
- `product_code`
- `patient_age_system`
- `patient_age_raw`
- `patient_age_manual`
- `result_label`
- `data_qc_conclusion`
- `bin_cv_1000k`
- `cnv_result`
- `chromosome_location`
- `cnv_hint`
- `result_detail`
- `incidental_manual`
- `aneuploidy_manual`

这些字段会直接影响：

- 有效胚胎筛选
- 医院筛选
- 时间筛选
- 周期量 / 胚胎量
- 整倍体率
- 质控情况
- 结果结构
- 特殊 CNV
- 意外发现
- 异倍体相关统计

---

## 建议字段结构

### 1. 技术字段

- `id`
- `snapshot_year`
- `snapshot_half`
- `import_batch_id`
- `source_file_name`
- `source_sheet_name`
- `source_row_num`
- `imported_at`

说明：

- `snapshot_half` 主要用于标记 `2023年7-12月`

### 2. 时间与机构字段

- `month_bucket`
- `report_review_time`
- `submission_time`
- `analysis_time`
- `hospital_name`
- `hospital_code`
- `region_name`
- `company_entity`

### 3. 订单与样本字段

- `product_code`
- `order_id`
- `order_code`
- `sample_barcode`
- `sample_id`
- `sample_name`
- `sample_type`
- `charged_sample_count`
- `sample_total_count`
- `received_sample_id`
- `case_id`

### 4. 人员与基础业务字段

- `doctor_name`
- `sales_name`
- `is_outsourced`
- `payment_method`
- `order_source`
- `business_type`

### 5. 受检人与配偶字段

- `patient_name`
- `patient_gender`
- `patient_age_system`
- `patient_age_raw`
- `patient_age_manual`
- `patient_chromosome`
- `patient_karyotype`
- `spouse_name`
- `spouse_gender`
- `spouse_age`
- `spouse_chromosome`
- `spouse_karyotype`
- `male_father_karyotype`
- `male_mother_karyotype`
- `female_father_karyotype`
- `female_mother_karyotype`

说明：

- `patient_age_system` 优先承接 `2025` 的 `受检人年龄（系统）`
- `patient_age_raw` 承接 `受检人年龄 / 女方年龄`
- `patient_age_manual` 承接人工处理年龄

### 6. 流转与实验字段

- `sample_date`
- `received_date`
- `input_time`
- `sample_status`
- `doctor_signed`
- `patient_signed`
- `order_info_complete`
- `transport_status`
- `temperature`
- `other_karyotype_info`
- `morphology_grade`
- `adaptation`
- `indication_raw`
- `indication_system`
- `indication_manual`
- `other_info`
- `resolution`
- `family_code`
- `amplification_method`
- `library_method`
- `run_no`
- `wga_kit_sku`
- `wga_kit_batch`
- `wga_concentration`
- `library_concentration`
- `cnv_kit_name`
- `cnv_kit_batch`

### 7. 测序与质控字段

- `raw_reads`
- `high_quality_rate`
- `mapping_rate`
- `duplication_rate`
- `unmapping_rate`
- `genome_coverage_rate`
- `valid_reads`
- `valid_reads_gc_content`
- `valid_reads_rate`
- `bin_cv_1000k`
- `seg_dd`
- `mt_cn`
- `data_qc_conclusion`
- `data_qc_information`

### 8. 结果字段

- `sex_karyotype`
- `cnv_result`
- `result_label`
- `cnv_hint`
- `chromosome_location`
- `result_detail`
- `aneuploidy_result_raw`
- `aneuploidy_manual`
- `incidental_raw`
- `incidental_manual`
- `result_note_1`
- `karyotype_abnormal_flag`
- `is_new_process`

---

## 年度字段兼容策略

### 2025

以 `2025年-数据` 作为主参考结构。

关键特点：

- 有 `受检人年龄（系统）`
- 有 `临床指征（系统）`
- 有 4 个关键人工处理字段

### 2026

与 `2025` 高度一致，但存在列名换行问题：

- `受检人年龄\n（人工处理）`
- `临床指征\n（人工处理）`
- `意外发现\n（人工处理）`
- `异倍体结果\n（人工处理）`

兼容规则：

- 导入前先做表头标准化，去掉中间换行
- `受检人年龄` 映射到 `patient_age_raw`

### 2024

与 `2025` 接近，但没有 `系统 / 人工处理` 双轨结构。

兼容规则：

- `受检人年龄` -> `patient_age_raw`
- `临床指征` -> `indication_raw`
- `异倍体分析` -> `aneuploidy_manual`
- `是否有意外发现` -> `incidental_raw`
- `性染色体核型` -> `sex_karyotype`

说明：

- `2024` 缺失 `受检人年龄（人工处理）`、`意外发现（人工处理）` 这类新字段时，允许对应标准列留空

### 2023年7-12月

和 `2024` 接近，但列略少。

兼容规则：

- `受检人年龄` -> `patient_age_raw`
- `临床指征` -> `indication_raw`
- `性染色体核型` -> `sex_karyotype`
- `异倍体分析（对应亲本污染分析字段）` -> `aneuploidy_result_raw`

## 当前建议的表头标准化规则

导入前建议统一做一轮轻量标准化：

1. 去掉换行
2. 去掉前后空格
3. 中文全角括号形式保持一致
4. 百分号和单位保留，不做激进改写

例如：

- `受检人年龄\n（人工处理）` -> `受检人年龄（人工处理）`
- `临床指征\n（人工处理）` -> `临床指征（人工处理）`
- `意外发现\n（人工处理）` -> `意外发现（人工处理）`
- `异倍体结果\n（人工处理）` -> `异倍体结果（人工处理）`

---

## 当前不要求的事情

本轮先不要求：

1. 和未来 API 字段一一完全对齐
2. 静态快照字段命名百分百保留原样
3. 为所有历史字段都设计统一业务语义
4. 把 `2023年1-6月` 纳入当前 SQLite 导入范围

---

## 结论

当前完全可以先落一张 `pgta_snapshot_raw` 表。

优先级建议：

1. 先定标准列名
2. 先保证当前底层统计函数依赖字段稳定映射
3. 年度差异字段做兼容导入，缺失允许为空
4. 后续如果某些旧年度字段确实不参与统计，再逐步收缩

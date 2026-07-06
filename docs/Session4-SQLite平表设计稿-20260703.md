# Session 4：SQLite 平表设计稿

## 设计结论

本轮 SQLite 设计采用最直接的过渡方案：

- 一个产品一张平表
- 来源直接对应当前快照里的明细源数据 sheet
- 表之间不做关联
- 不提前抽公共业务字段
- 不为这批过渡快照设计长期统一模型

原因：

1. 当前快照本质是过渡执行源，不是长期主数据模型
2. 后续真实版本预计按产品走实时 API，不会天然落成一张统一总表
3. 当前优先级是让多产品真实统计尽快可执行，而不是做优雅统一建模

---

## 范围

当前只设计以下 4 张主表：

1. `pgta_snapshot_2025_data`
2. `pgtsr_snapshot_2025_data`
3. `pgtah_snapshot_2025_source`
4. `pgtm_snapshot_raw_data`

对应来源：

1. `PGTA`：`2025年-数据`
2. `PGTSR`：`2025年-数据`
3. `PGTAH`：`2025源数据`
4. `PGTM`：`原始数据`

透视页、统计页、输出页当前不进入执行主表，只作为：

- 导入校验参考
- 业务口径核对参考

---

## 通用约束

虽然不做跨产品整合，但每张表仍建议补一组最小技术字段，用于导入可追溯和重复构建。

每张表建议额外补充：

- `id`
- `import_batch_id`
- `source_row_num`
- `source_file_name`
- `source_sheet_name`
- `imported_at`

说明：

- 这些字段是技术元数据，不是公共业务抽象
- 作用是帮助定位导入问题、支持重建和追溯

---

## 导入批次表

建议新增一张轻量元数据表：

`snapshot_import_batch`

建议字段：

- `id`
- `product_code`
- `table_name`
- `source_file_name`
- `source_sheet_name`
- `source_file_size`
- `source_file_mtime`
- `import_started_at`
- `import_finished_at`
- `row_count_raw`
- `row_count_loaded`
- `status`
- `notes`

作用：

- 记录一次 Excel 导入任务
- 帮助判断当前 SQLite 数据是否需要重建
- 给调试和回归提供版本感知

---

## 主表 1：PGTA

表名：

`pgta_snapshot_2025_data`

来源：

- 文件：[PGTA数据统计输出-2025年.xlsx](/home/zhangly/repo/github/yk-hospital-data-review-agent/docs/PGTA数据统计输出-2025年.xlsx)
- Sheet：`2025年-数据`

建议保留原列为主，只做必要的英文命名映射。

建议字段分组：

技术字段：

- `id`
- `import_batch_id`
- `source_row_num`
- `source_file_name`
- `source_sheet_name`
- `imported_at`

时间与机构：

- `month_bucket`
- `report_review_time`
- `project_type`
- `company_entity`
- `hospital_name`
- `region_name`

订单与样本：

- `product_code`
- `order_id`
- `order_code`
- `charged_sample_count`
- `sample_total_count`
- `sample_id`
- `sample_name`
- `sample_type`
- `received_sample_id`
- `case_id`

人员与业务：

- `doctor_name`
- `sales_name`
- `is_outsourced`
- `payment_method`
- `order_source`
- `business_type`

受检人与家系：

- `patient_name`
- `patient_gender`
- `patient_age_system`
- `patient_chromosome`
- `patient_karyotype`
- `spouse_name`
- `spouse_gender`
- `spouse_age`
- `spouse_chromosome`
- `spouse_karyotype`
- `father_karyotype_male`
- `mother_karyotype_male`
- `father_karyotype_female`
- `mother_karyotype_female`

样本流转与实验：

- `sample_date`
- `sample_status`
- `doctor_signed`
- `patient_signed`
- `order_info_complete`
- `transport_status`
- `temperature`
- `other_karyotype_info`
- `received_date`
- `input_time`
- `morphology_grade`
- `indication`
- `indication_system`
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

测序与质控：

- `raw_reads`
- `high_quality_rate`
- `mapping_rate`
- `duplication_rate`
- `genome_coverage_rate`
- `valid_reads`
- `valid_reads_gc_content`
- `valid_reads_rate`
- `bin_cv_1000k`
- `data_qc_conclusion`

结果字段：

- `cnv_result`
- `result_label`
- `cnv_hint`
- `chromosome_location`
- `result_detail`
- `aneuploidy_result_raw`
- `result_note_1`

人工处理字段：

- `patient_age_manual`
- `indication_manual`
- `incidental_manual`
- `aneuploidy_manual`

说明：

- `PGTA` 的人工处理字段对当前口径非常关键，不能丢
- 后续迁移查询时，优先继续吃这些人工处理列

---

## 主表 2：PGTSR

表名：

`pgtsr_snapshot_2025_data`

来源：

- 文件：[PGTSR数据统计输出-2025年.xlsx](/home/zhangly/repo/github/yk-hospital-data-review-agent/docs/PGTSR数据统计输出-2025年.xlsx)
- Sheet：`2025年-数据`

建议保留与 `PGTA` 相近的基础列，同时保留 SR 专有字段。

建议字段分组：

技术字段：

- `id`
- `import_batch_id`
- `source_row_num`
- `source_file_name`
- `source_sheet_name`
- `imported_at`

基础业务字段：

- `month_bucket`
- `report_review_time`
- `project_type`
- `company_entity`
- `hospital_name`
- `region_name`
- `product_code`
- `order_id`
- `order_code`
- `charged_sample_count`
- `sample_total_count`
- `doctor_name`
- `sales_name`
- `is_outsourced`
- `payment_method`
- `order_source`
- `business_type`
- `patient_name`
- `patient_gender`
- `patient_age`
- `patient_chromosome`
- `patient_karyotype`
- `spouse_name`
- `spouse_gender`
- `spouse_age`
- `spouse_chromosome`
- `spouse_karyotype`
- `sample_date`
- `sample_status`
- `doctor_signed`
- `patient_signed`
- `order_info_complete`
- `transport_status`
- `temperature`
- `other_karyotype_info`
- `received_date`
- `input_time`
- `sample_id`
- `sample_name`
- `sample_type`
- `received_sample_id`
- `morphology_grade`
- `case_id`
- `adaptation`
- `indication`
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
- `raw_reads`
- `high_quality_rate`
- `mapping_rate`
- `duplication_rate`
- `genome_coverage_rate`
- `valid_reads`
- `valid_reads_gc_content`
- `valid_reads_rate`
- `bin_cv_1000k`
- `data_qc_conclusion`
- `cnv_result`
- `result_label`
- `cnv_hint`
- `chromosome_location`
- `result_detail`
- `aneuploidy_result_raw`
- `result_note_1`

SR 专有字段：

- `breakpoint_result`
- `is_marecs_stage2`
- `marecs_stage2_family_type`
- `is_next_step_translocation_screening`
- `evaluation_annotation`
- `aneuploidy_manual`
- `incidental_manual`

说明：

- `PGTSR` 关键不是统一到 `PGTA` 口径，而是完整保住二阶段和下一步筛查字段
- 这些字段决定后续 SR 真实指标是否能快速落地

---

## 主表 3：PGTAH

表名：

`pgtah_snapshot_2025_source`

来源：

- 文件：[PGTAH数据统计输出-2025年-上传微盘.xlsx](/home/zhangly/repo/github/yk-hospital-data-review-agent/docs/PGTAH数据统计输出-2025年-上传微盘.xlsx)
- Sheet：`2025源数据`

当前 `PGTAH` 字段结构比 `PGTA` 简单，可先保持平移导入，不额外抽象。

建议字段分组：

技术字段：

- `id`
- `import_batch_id`
- `source_row_num`
- `source_file_name`
- `source_sheet_name`
- `imported_at`

基础业务字段：

- `month_bucket`
- `report_review_time`
- `project_type`
- `company_entity`
- `hospital_name`
- `region_name`
- `product_code`
- `order_id`
- `order_code`
- `charged_sample_count`
- `sample_total_count`
- `doctor_name`
- `sales_name`
- `is_outsourced`
- `payment_method`
- `order_source`
- `business_type`
- `patient_name`
- `patient_gender`
- `patient_age`
- `patient_chromosome`
- `patient_karyotype`
- `spouse_name`
- `spouse_gender`
- `spouse_age`
- `spouse_chromosome`
- `spouse_karyotype`
- `sample_date`
- `sample_status`
- `doctor_signed`
- `patient_signed`
- `order_info_complete`
- `transport_status`
- `temperature`
- `other_karyotype_info`
- `received_date`
- `input_time`
- `sample_id`
- `sample_name`
- `sample_type`
- `received_sample_id`
- `morphology_grade`
- `case_id`
- `adaptation`
- `indication`
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
- `raw_reads`
- `high_quality_rate`
- `mapping_rate`
- `duplication_rate`
- `genome_coverage_rate`
- `valid_reads`
- `valid_reads_gc_content`
- `valid_reads_rate`
- `bin_cv_1000k`
- `data_qc_conclusion`
- `cnv_result`
- `result_label`
- `cnv_hint`
- `chromosome_location`
- `result_detail`
- `aneuploidy_result_raw`
- `result_note_1`
- `incidental_flag_raw`

说明：

- `PGTAH` 后续如果真实执行需求扩大，再考虑是否补独立衍生列
- 当前先按原表平移最稳

---

## 主表 4：PGTM

表名：

`pgtm_snapshot_raw_data`

来源：

- 文件：[2025-PGTM类全年输出.xlsx](/home/zhangly/repo/github/yk-hospital-data-review-agent/docs/2025-PGTM类全年输出.xlsx)
- Sheet：`原始数据`

`PGTM` 的专有字段最多，建议完整保留，不尝试与其他产品抽象合并。

建议字段分组：

技术字段：

- `id`
- `import_batch_id`
- `source_row_num`
- `source_file_name`
- `source_sheet_name`
- `imported_at`

基础业务字段：

- `report_review_time`
- `project_date`
- `project_type`
- `company_entity`
- `hospital_name`
- `region_name`
- `product_code`
- `order_id`
- `order_code`
- `charged_sample_count`
- `sample_total_count`
- `doctor_name`
- `sales_name`
- `is_outsourced`
- `payment_method`
- `order_source`
- `business_type`
- `patient_name`
- `patient_gender`
- `patient_age`
- `patient_chromosome`
- `patient_karyotype`
- `spouse_name`
- `spouse_gender`
- `spouse_age`
- `spouse_chromosome`
- `spouse_karyotype`
- `sample_date`
- `sample_status`
- `doctor_signed`
- `patient_signed`
- `order_info_complete`
- `transport_status`
- `temperature`
- `other_karyotype_info`
- `received_date`
- `input_time`
- `sample_id`
- `sample_name`
- `sample_type`
- `received_sample_id`
- `morphology_grade`
- `case_id`
- `adaptation`
- `indication`
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
- `raw_reads`
- `high_quality_rate`
- `mapping_rate`
- `duplication_rate`
- `genome_coverage_rate`
- `valid_reads`
- `valid_reads_gc_content`
- `valid_reads_rate`
- `bin_cv_1000k`
- `data_qc_conclusion`

PGTM 专有字段：

- `gene_name`
- `inheritance_mode`
- `variant_chgvs`
- `qc_conclusion`
- `qc_information`
- `detection_rate_autosome`
- `ado_rate_autosome`
- `mendel_error_rate_autosome`
- `disease_name`
- `cnv_result`
- `result_label`
- `variant_carrier_result`
- `aneuploidy_result_raw`
- `result_note_2`
- `variant_detection_result`
- `result_consistency`
- `result_note_3`
- `family_type`
- `is_linkage_analysis`
- `cnv_hint`
- `chromosome_location`
- `result_detail`
- `comma_flag`
- `percent_flag`
- `mosaic_only_flag`
- `cnv_result_dup`
- `snp_carrier_status`
- `carrier_status_adjusted`
- `not_carrier_flag_text`
- `carrier_flag_text`
- `not_carrier_count`
- `carrier_count`
- `carrier_count_delta`

说明：

- `PGTM` 中部分列名带明显人工中间态痕迹，建议先原样保住
- 等真实指标口径收敛后，再决定是否在查询层二次清洗

---

## 索引建议

当前不做统一模型，因此索引也以“每张平表各自可查”为目标。

每张主表建议至少建立：

- `hospital_name`
- `report_review_time`
- `sample_id`
- `order_id`

如果表中有 `month_bucket`，再补：

- `month_bucket`
- `(hospital_name, month_bucket)`

对 `PGTM` 可考虑额外补：

- `project_date`
- `gene_name`
- `disease_name`

对 `PGTSR` 可考虑额外补：

- `is_marecs_stage2`
- `is_next_step_translocation_screening`

---

## 当前不做的事情

本设计稿明确不做：

1. 不做跨产品统一事实表
2. 不做表间外键关联
3. 不做公共业务字段抽象层
4. 不做跨产品共享 SQL 模型
5. 不为未来正式 API 预设统一数据库结构

---

## 推荐的后续文档与实现顺序

1. 先用本文档确定 4 张平表和导入批次表
2. 再补一页“Excel 列名 -> SQLite 列名映射清单”
3. 再补一页“PGTA 先迁移的查询字段使用清单”
4. 之后再进入 importer 和查询迁移代码实现

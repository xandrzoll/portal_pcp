SELECT
      date_report dt
    , employee_id tab_num
	, urf_code_uni vsp
	, 0 expense_type
	, employee_position_gr pos_gr
	, SUM(quantity) expense_cnt
FROM "001_MIS_RETAIL_REPORTING"."vasm_operations"
WHERE 1=1
	and (PRODUCT_ID = 435 or PRODUCT_ID = 558 or PRODUCT_ID = 557 or PRODUCT_ID = 559 or PRODUCT_ID = 613 or PRODUCT_ID = 635)
	and (OPERATION_ID = 118 or OPERATION_ID = 268)
	and date_month >= date'{dt}'
GROUP BY 1, 2, 3, 4, 5
SELECT
	lpad(REGEXP_substr(page.vsp_name, '\d+', 1, 2), 4, '0')  ||'_'|| lpad(REGEXP_substr(page.vsp_name, '\d+', 1, 3), 5, '0') as gosb_vsp
	,page.tb_name As tb
	,page.gosb as gosb_name
	,REGEXP_substr(page.vsp_name, '\d+', 1, 2) as gosb
	,REGEXP_substr(page.vsp_name, '\d+', 1, 3) as vsp
	,Case 
		When page.staff_group_id = 'Физики' Then 'обслуживание физических лиц'
		When page.staff_group_id = 'Юрики'  Then 'обслуживание юридических лиц'
		ELSE 'Что - то не так'
	END as category_serv
	,stat_r.Depart_Subject as subj_RF
	,stat_r.FA_Locality_name as city
	,COALESCE(stat_r.FA_street_name,'') || COALESCE (', ' || substr(stat_r.FA_house, 2), '') || COALESCE (', ' || stat_r.FA_Addres_add,'') as address
	,page.city_full as full_address
	,page."DATE" as dt
	,page.work_time as worktime
	,Case 
		When dinner_time is null Then 'нет'
		When dinner_time is not null Then dinner_time
		ELSE 'Что - то не так'
	END as dinner_time
	,page.vip
	,stat_r.FA_METRO
FROM  "001_MIS_RETAIL_CHANNEL".v_rost_iurr_schedule_vsp_day_by_day as page
left join  "001_MIS_RETAIL_CHANNEL".V_500_001_DBD_ALL_CUR_TBAL as stat_r
    on  lpad(REGEXP_substr(page.vsp_name, '\d+', 1, 2), 4, '0')  = lpad(trim(substr(stat_r.depart_code, 4, 4)), 4, '0') 
    and lpad(REGEXP_substr(page.vsp_name, '\d+', 1, 3), 5, '0')  = lpad(trim(substr(stat_r.depart_code, 8, 5)), 5, '0')
Where 1=1
    and page.work_time is not null
    and page."DATE" between date'{}' and date'{}'
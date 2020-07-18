sql_shema = 'select type, name, tbl_name, rootpage, sql from SQLITE_MASTER'

sql_orders_in_work = '''
select 
    T1.id, 
    T1.dttm, 
    T1.dep_id, 
    T1.vsp, 
    T1.status, 
    T1.address, 
    T1.client_short, 
    T1.phone, 
    (select id from SIMS_ORDERS where dttm >= date(T1.dttm, '-14 day') and (vsp=T1.vsp or dep_id=T1.dep_id)  and id <> T1.id order by dttm desc limit 1) as id_prev_14,
    (select id from SIMS_DELIVERY where vsp=T1.vsp order by dt desc limit 1) as id_prev_delivery,
    (select dt from SIMS_DELIVERY where vsp=T1.vsp order by dt desc limit 1) as dt_prev_delivery,
    (select delivery_cnt from SIMS_DELIVERY where vsp=T1.vsp order by dt desc limit 1) as count_prev_delivery,
    (select sum(expense_cnt) as sales from SIMS_expense where vsp = T1.vsp) as sales_all,
    (select sum(case when dt >= date('now', 'start of month') then expense_cnt else 0 end) as sales from SIMS_expense where vsp = T1.vsp) as sales_current,
    (select sum(case when dt >= date('now', 'start of month', '-1 month') and dt <= date('now', 'start of month', '-1 day') then expense_cnt else 0 end) as sales from SIMS_expense where vsp = T1.vsp) as sales_prev1,
    (select sum(case when dt >= date('now', 'start of month', '-2 month') and dt <= date('now', 'start of month', '-1 month', '-1 day') then expense_cnt else 0 end) as sales from SIMS_expense where vsp = T1.vsp) as sales_prev2
from SIMS_ORDERS as T1
where T1.status not in ('Закрыто', 'Выполнено')
'''

url_order = 'https://sudirall.ca.sbrf.ru/podruga/index.do?ctx=docEngine&file=incidents&query=incident.id%3D%22{}%22&action=&title='

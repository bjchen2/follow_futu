import winsound

import init_param
import lycMonitor

from futu import *
import futuTrade

#总资产
total_money = 10000
def compare_buy(position_dict, current_dict, futu_order):
    # 找出删除的记录
    for stock_code, record in position_dict.items():
        if stock_code not in current_dict:
            futu_order.place_order(stock_code=stock_code, trde_env=TrdEnv.SIMULATE, qty=-record['qty'])

    # 找出更新的记录
    for stock_code, current_record in current_dict.items():
        if stock_code in position_dict:
            record = position_dict[stock_code]
            current_total = current_record.total_ratio * total_money / 100
            position_total = record['market_val']
            diff = current_total - position_total
            if abs(diff) > 300:
                futu_order.place_order(stock_code, diff, current_record.current_price, TrdEnv.SIMULATE)

    # 找出新增的记录
    for stock_code, record in current_dict.items():
        if stock_code not in position_dict:
            futu_order.place_order(stock_code, record.total_ratio * total_money / 100, record.current_price, TrdEnv.SIMULATE)


def trade(market = TrdMarket.US, env = TrdEnv.SIMULATE):
    url = init_param.us_monitor_url if market == TrdMarket.US else init_param.hk_monitor_url
    monitor = lycMonitor.PortfolioMonitor(url)
    # 初始化下单工具
    futu_order = futuTrade.FutuOrder()
    print("开始监控投资组合变化...")
    prefix_code = market + "."

    while True:
        try:
            wait_time = lycMonitor.get_monitor_sleep_sec(market=market)
            if wait_time is None:
                futuTrade.append_log(f"监控结束，market={market}")
                time.sleep(60 * 30)
                continue
            ret, data = futu_order.position_list_query()
            position_dict = {row['code']: row.to_dict() for _, row in data.iterrows() if row['qty'] != 0}

            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 正在检查...")

            if position_dict:
                global total_money
                total_money = max(sum(obj['market_val'] for obj in position_dict.values()), 10000)

            current_pos = monitor.fetch_data()
            for obj in current_pos.values():
                obj.stock_code = prefix_code + obj.stock_code
            current_pos = {v.stock_code : v for k,v in current_pos.items()}
            compare_buy(position_dict, current_pos, futu_order)


            # if first:
            #     compare_buy(position_dict, diff, futu_order)
                # first = False
                # continue

            # if diff.sale:
            #     for obj in diff.sale:
            #         position_obj = position_dict[obj.stock_code]
            #         if obj.clear and position_obj:
            #             #清仓
            #             qty = position_obj['qty']
            #             futu_order.place_order(stock_code=obj.stock_code, trde_env=env, qty=-qty)
            #         else:
            #             current_total = obj.total_ratio * total_money / 100
            #             position_total = position_obj['market_val'] if position_obj else 0
            #             diff_amount = current_total - position_total
            #             futu_order.place_order(obj.stock_code, diff_amount, obj.current_price, TrdEnv.SIMULATE)

            # if diff.buy:
            #     for obj in diff.buy:
            #         position_obj = position_dict[obj.stock_code]
            #         current_total = obj.total_ratio * total_money / 100
            #         position_total = position_obj['market_val'] if position_obj else 0
            #         diff_amount = current_total - position_total
            #         futu_order.place_order(obj.stock_code, diff_amount, obj.current_price, TrdEnv.SIMULATE)

            # if diff.buy or diff.sale:
            #     futuTrade.append_log(content="\n", add_timestamp=False)


            print(f"等待 {wait_time:.3f} 秒后进行下次检查...")
            time.sleep(wait_time)

        except Exception as e:
            print(f"发生错误: {e}")
            traceback.print_exc()
            winsound.Beep(440, 500)
            time.sleep(60)  # 出错后等待1分钟再重试

if __name__ == "__main__":
    trade()
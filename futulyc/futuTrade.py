import math

import winsound
from futu import *

import time

import init_param


def append_log(
        content: str,
        log_file: str = "logInfo.txt",
        add_timestamp: bool = True
) -> None:
    """
    追加日志到指定文件，默认添加时间戳、写入 logInfo.txt

    :param content: 日志内容（必填，如"等待 3.500 秒后进行下次检查..."）
    :param log_file: 日志文件名，默认"logInfo.txt"
    :param add_timestamp: 是否添加时间戳，默认True（格式：2024-05-20 14:30:05）
    """
    try:
        # 1. 处理时间戳（格式：年-月-日 时:分:秒）
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) if add_timestamp else ""
        # 2. 构造最终日志行（时间戳+内容，空时间戳则直接用内容）
        log_line = f"[{timestamp}] {content}\n" if add_timestamp else f"{content}\n"

        # 3. 追加写入文件（utf-8编码避免中文乱码，with自动关闭文件）
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)
            print(log_line)

    except Exception as e:
        # 捕获异常并打印（避免日志写入失败导致主程序崩溃）
        print(f"日志写入失败！原因：{str(e)}")

def get_trd_accid(trd_env, trd_market):
    if trd_env == TrdEnv.REAL:
        if trd_market == TrdMarket.US:
            return init_param.us_prod_accid
        elif trd_market == TrdMarket.HK:
            return init_param.hk_prod_accid
    elif trd_env == TrdEnv.SIMULATE:
        if trd_market == TrdMarket.US:
            return init_param.us_test_accid
        elif trd_market == TrdMarket.HK:
            return init_param.hk_test_accid
    return None


class FutuOrder:
    def __init__(self, market=TrdMarket.US, trd_env=TrdEnv.SIMULATE):
        """
        初始化富途下单工具
        """
        self.market = market
        self.trd_env = trd_env
        self.prefix_code = market + "."
        self.trd_ctx = OpenSecTradeContext(filter_trdmarket=market,host='127.0.0.1', port=11111)  # 创建交易对象

    #查询当前账户持仓
    def position_list_query(self):
        return self.trd_ctx.position_list_query(acc_id=self.get_accid(), trd_env=self.trd_env, position_market=self.market)

    def accinfo_query(self):
        return self.trd_ctx.accinfo_query(acc_id=self.get_accid(), trd_env=self.trd_env, currency=Currency.USD if self.market==TrdMarket.US else Currency.HKD)

    def get_can_use_money(self):
        ret,acc_info = self.accinfo_query()
        can_use_money = acc_info['total_assets'][0] - acc_info['market_val'][0]  - (990000 if self.trd_env == TrdEnv.SIMULATE else 0)
        return max(0, can_use_money)

    def get_accid(self):
        return get_trd_accid(trd_env=self.trd_env, trd_market=self.market)

    #下单
    def place_order(self, stock_code, invest_amount=None, last_price=None, qty=None):
        time.sleep(0.1)
        acc_id = self.get_accid()

        trd_obj = dict()
        trd_obj['code'] = stock_code
        trd_obj['股数'] = qty
        trd_obj['trd_side'] = ''
        trd_obj['总交易额'] = invest_amount
        trd_obj['单价'] = last_price
        trd_obj['acc_id'] = acc_id
        trd_obj['trd_env'] = self.trd_env
        if qty is None:
            # 获取最新价格
            if not last_price or last_price <= 0 or not invest_amount:
                append_log(f"[下单] 单价无效 trd_obj={trd_obj}")
                return
            if invest_amount > 0:
                #买入操作，判断金额是否足够
                can_use_money = self.get_can_use_money()
                if can_use_money < invest_amount:
                    append_log(f"[下单] 可用金额不足，can_use_money={can_use_money} trd_obj={trd_obj}")
                    invest_amount = can_use_money

            trd_side = TrdSide.SELL if invest_amount < 0 else TrdSide.BUY
            invest_amount = abs(invest_amount)
            # 计算股数，向下取整
            qty = math.floor(invest_amount / last_price)
        else:
            #必须赋值price
            last_price=1
            trd_side = TrdSide.SELL if qty < 0 else TrdSide.BUY
            qty = abs(qty)

        trd_obj['股数'] = qty
        trd_obj['trd_side'] = trd_side
        trd_obj['总交易额'] = invest_amount
        trd_obj['单价'] = last_price
        if qty <= 0:
            append_log(f"[下单] 可下单股数无效 trd_obj={trd_obj}")
            return
        if self.trd_env == TrdEnv.REAL:
            #先解锁，再下单
            self.trd_ctx.unlock_trade(init_param.pwd_unlock)
        ret,data=self.trd_ctx.place_order(acc_id=acc_id, order_type=OrderType.MARKET,price=last_price, qty=qty, code=stock_code, trd_side=trd_side, trd_env=self.trd_env)
        append_log(f"[下单] 下单成功 trd_obj={trd_obj}, ret={ret}, \ndata={data}")
        while ret == -1:
            #下单失败，一直告警
            winsound.Beep(800, 100)
            time.sleep(0.2)
        winsound.Beep(440, 500)

    def __del__(self):
        self.trd_ctx.close()  # 关闭对象，防止连接条数用尽

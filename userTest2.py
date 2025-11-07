from futu import *

trd_ctx = OpenSecTradeContext(filter_trdmarket=TrdMarket.US,host='127.0.0.1', port=11111)  # 创建交易对象
pd.set_option('display.max_columns', None)  # None 表示不限制列数

print(trd_ctx.get_acc_list())
trd_ctx.close()  # 关闭对象，防止连接条数用尽

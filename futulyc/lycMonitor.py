import copy
import datetime

import requests
import time
import json
import random
from typing import Dict, List, Any
from dataclasses import dataclass, field

import init_param


@dataclass
class Record:
    stock_code: str
    total_ratio: float
    position_ratio: float
    cost_price: float
    current_price:float
    profit_and_loss_ratio: float
    change_ratio: float = 0.0
    clear: bool = False

@dataclass
class RecordDiff:
    buy: List[Record] = field(default_factory=list)
    sale: List[Record] = field(default_factory=list)

class PortfolioMonitor:
    def __init__(self, url: str):
        self.url = url
        self.previous_records = {}
        self.first_run = True

    def fetch_portfolio_data(self) -> Dict[str, Any]:
        """获取投资组合数据"""
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return None

    def extract_records(self, data: Dict[str, Any]) -> Dict[str, Record]:
        """提取记录并以stock_code为key建立字典"""
        if not data or 'data' not in data or 'record_items' not in data['data']:
            return {}

        records = {}
        for item in data['data']['record_items']:
            if 'stock_code' in item:
                record = Record(
                    stock_code=item['stock_code'],
                    total_ratio=item.get('total_ratio', 0)/10e6,
                    position_ratio=item.get('position_ratio', 0)/10e6,
                    cost_price=item.get('cost_price', 0)/10e8,
                    current_price=item.get('current_price', 0)/10e8,
                    profit_and_loss_ratio=item.get('profit_and_loss_ratio', 0)/10e6
                )
                records[item['stock_code']] = record

        return records

    def compare_records(self, current_records: Dict[str, Record]) -> RecordDiff:
        """比较当前记录和上次记录的差异"""
        diff = RecordDiff()

        # 如果是第一次运行，所有记录都是新增的
        if self.first_run:
            diff.buy = list(current_records.values())
            self.first_run = False
        else:
            # 找出新增的记录
            for stock_code, record in current_records.items():
                if stock_code not in self.previous_records:
                    diff_record = copy.deepcopy(current_records[stock_code])
                    diff_record.change_ratio = current_records[stock_code].total_ratio
                    diff.buy.append(diff_record)

            # 找出删除的记录
            for stock_code, record in self.previous_records.items():
                if stock_code not in current_records:
                    diff_record = copy.deepcopy(self.previous_records[stock_code])
                    diff_record.change_ratio = -self.previous_records[stock_code].total_ratio
                    diff_record.clear = True
                    diff.sale.append(diff_record)

            # 找出更新的记录（total_ratio变化大于3）
            for stock_code, current_record in current_records.items():
                if stock_code in self.previous_records:
                    previous_record = self.previous_records[stock_code]
                    ratio_diff = abs(current_record.total_ratio - previous_record.total_ratio)
                    if ratio_diff > 3:
                        diff_record = copy.deepcopy(current_record)
                        if current_record.total_ratio > previous_record.total_ratio:
                            diff_record.change_ratio = ratio_diff
                            diff.buy.append(diff_record)
                        elif current_record.total_ratio < previous_record.total_ratio:
                            diff_record.change_ratio = -ratio_diff
                            diff.sale.append(diff_record)
        return diff

    def fetch_data(self)-> Dict[str, Record]:
        """执行一次监控，返回差异结果"""
        # 获取当前数据
        data = self.fetch_portfolio_data()
        if not data:
            return {}

        # 提取记录
        return self.extract_records(data)

    def monitor(self) -> RecordDiff:
        """执行一次监控，返回差异结果"""
        # 获取当前数据
        data = self.fetch_portfolio_data()
        if not data:
            return RecordDiff()

        # 提取记录
        current_records = self.extract_records(data)

        # 比较差异
        diff = self.compare_records(current_records)

        # 更新上次记录
        self.previous_records = current_records.copy()

        return diff

def print_record_diff(diff: RecordDiff):
    """打印记录差异"""
    print("发现变更:")
    if diff.buy:
        print("  新增记录:")
        for record in diff.buy:
            print(f"    - 股票代码: {record.stock_code}")
            print(f"      总比例: {record.total_ratio}")
            print(f"      持仓比例: {record.position_ratio}")
            print(f"      成本价: {record.cost_price}")
            print(f"      盈亏比例: {record.profit_and_loss_ratio}")
            print(f"      变动比例: {record.change_ratio}")
            print()

    if diff.sale:
        print("  删除记录:")
        for record in diff.sale:
            print(f"    - 股票代码: {record.stock_code}")
            print(f"      总比例: {record.total_ratio}")
            print(f"      持仓比例: {record.position_ratio}")
            print(f"      成本价: {record.cost_price}")
            print(f"      盈亏比例: {record.profit_and_loss_ratio}")
            print(f"      变动比例: {record.change_ratio}")
            print()

    if not diff.buy and not diff.sale:
        print("  无变更")


from datetime import datetime


def get_monitor_sleep_sec(market='US'):
    # 获取当前时间（仅包含时分信息）
    now = datetime.now().time()

    trading = False
    if market == 'US':
        # 判断是否在22:30-5:00（跨天时间段）
        start = datetime.strptime('22:30', '%H:%M').time()
        end = datetime.strptime('05:00', '%H:%M').time()
        # 跨天情况：当前时间 >= 开始时间 或 当前时间 <= 结束时间
        trading = now >= start or now <= end

    elif market == 'HK':
        # 第一个时间段：9:30-12:00
        start1 = datetime.strptime('09:30', '%H:%M').time()
        end1 = datetime.strptime('12:00', '%H:%M').time()
        # 第二个时间段：13:00-16:00
        start2 = datetime.strptime('13:00', '%H:%M').time()
        end2 = datetime.strptime('16:00', '%H:%M').time()
        # 满足任一时间段即返回True
        trading = (start1 <= now <= end1) or (start2 <= now <= end2)

    if trading:
        # 随机等待30-60秒（毫秒级别差异）
        return random.randint(30000, 60000) / 1000.0
    elif market == 'US':
        return None
        # 随机等待3-6min（毫秒级别差异）
        # return random.randint(3 * 60000, 6 * 60000) / 1000.0
    return None


def main():
    url = init_param.us_monitor_url

    monitor = PortfolioMonitor(url)

    print("开始监控投资组合变化...")

    while True:
        try:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 正在检查...")

            diff = monitor.monitor()
            print_record_diff(diff)

            # 随机等待30-60秒（毫秒级别差异）
            wait_time = random.randint(30000, 60000) / 1000.0
            print(f"等待 {wait_time:.3f} 秒后进行下次检查...")
            time.sleep(wait_time)

        except KeyboardInterrupt:
            print("\n监控已停止")
            break
        except Exception as e:
            print(f"发生错误: {e}")
            time.sleep(60)  # 出错后等待1分钟再重试

if __name__ == "__main__":
    main()
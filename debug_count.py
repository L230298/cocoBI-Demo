"""查询:同一用户是否多次购买同一配置"""
import pandas as pd

file_path = r"c:\Users\huawei\Desktop\cocobi-demo\backend\data\uploads\4960b9cc4184.xlsx"
df = pd.read_excel(file_path)
df['buy_time'] = pd.to_datetime(df['buy_time'])

# 限定 5月 + mac pro 32G 1T
sub = df[
    (df['buy_time'] >= '2026-05-01') &
    (df['buy_time'] < '2026-06-01') &
    (df['device_config'] == 'mac pro 32G 1T')
]

print(f"5月 + mac pro 32G 1T:")
print(f"  记录数:           {len(sub)}")
print(f"  去重用户数:       {sub['user_id'].nunique()}")
print(f"  去重订单数:       {sub['order_id'].nunique()}")
print()

# 关键:每个 user 买了几次?
print("=" * 60)
print("每个 user 购买 mac pro 32G 1T 的次数:")
print("=" * 60)
counts = sub.groupby('user_id').size().reset_index(name='count')
print(counts.to_string(index=False))
print()
print("购买 > 1 次的用户数:", (counts['count'] > 1).sum())
print()

# 整个数据集层面
print("=" * 60)
print("整个数据集:同一 user 买同一 config 多次的情况:")
print("=" * 60)
all_counts = df.groupby(['user_id', 'device_config']).size().reset_index(name='count')
dups = all_counts[all_counts['count'] > 1]
if len(dups) == 0:
    print("  (无 — 整个数据集里没有任何用户重复购买同一配置)")
else:
    print(dups.to_string(index=False))
print()

# 看看数据分布
print("=" * 60)
print("完整统计:")
print("=" * 60)
print(f"  总行数:               {len(df)}")
print(f"  不同 user 数:         {df['user_id'].nunique()}")
print(f"  不同 order 数:        {df['order_id'].nunique()}")
print(f"  不同 device_config:   {df['device_config'].nunique()}")
print(f"  不同 buy_time 月份:   {df['buy_time'].dt.strftime('%Y-%m').nunique()}")
print()
print("每个 user_id 出现次数分布:")
user_freq = df.groupby('user_id').size()
print(user_freq.value_counts().to_string())
print()
print("→ 即:每个 user_id 在整个数据集出现 5 次(对应 5 种配置各 1 次)")

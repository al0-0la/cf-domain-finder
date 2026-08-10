# Cloudflare Domain Finder

从 Cloudflare 优选域名池中筛选最适合目标域名的 Cloudflare IP。

项目会：

1. 获取 VPS789 推荐优选域名
2. 合并本地维护域名列表
3. DNS 查询全部 A 记录
4. 使用目标域名进行 Cloudflare 回源测试
5. 统计成功率
6. 统计失败率
7. 统计平均 TTFB
8. 排名输出
9. 生成 CSV 报表

---

# 工作原理

例如：

目标域名：

```python
TARGET_DOMAIN = "saas.example.com"
```

优选域名：

```text
cf.tencentapp.cn
time.is
cf.blogluo.eu.org
www.oopt.eu.cc
```

首先解析：

```text
cf.tencentapp.cn

104.16.1.1
104.16.1.2
172.67.6.1
```

然后逐个测试：

```bash
curl \
--resolve saas.example.com:443:104.16.1.1 \
https://saas.example.com/cdn-cgi/trace
```

判断：

```text
是否成功
colo
TTFB
```

最终找出：

- 哪个优选域名最稳定
- 哪个优选域名失败率最低
- 哪个优选域名速度最快

---

# 数据来源

## VPS789

接口：

```text
https://vps789.com/public/sum/cfIpTop20
```

示例：

```json
{
  "ip": "cf.blogluo.eu.org",
  "avgScore": 150,
  "avgLatency": 109,
  "avgPkgLostRate": 0.83
}
```

注意：

这里的 `ip` 字段实际上是域名。

程序会自动转换为候选域名进行测试。

---

## 本地域名池

修改：

```python
config.py
```

中的：

```python
STATIC_DOMAINS
```

即可增加自己的优选域名。

---

# 环境要求

Python：

```text
>= 3.10
```

推荐：

```text
Python 3.11
Python 3.12
Python 3.13
```

---

# Linux依赖

程序依赖：

```text
curl
dig
```

Ubuntu / Debian：

```bash
sudo apt update

sudo apt install -y \
curl \
dnsutils
```

CentOS：

```bash
sudo yum install -y \
curl \
bind-utils
```

AlmaLinux：

```bash
sudo dnf install -y \
curl \
bind-utils
```

---

# 安装

克隆项目：

```bash
git clone https://github.com/al0-0la/cf-domain-finder.git

cd cf-domain-finder
```

安装依赖：

```bash
pip install -r requirements.txt
```

---

# 配置

编辑：

```python
config.py
```

修改目标域名：

```python
TARGET_DOMAIN = "saas.example.com"
```

修改最大并发：

```python
MAX_CONCURRENT = 300
```

修改超时时间：

```python
CONNECT_TIMEOUT = 5

MAX_TIME = 10
```

---

# 运行

```bash
python main.py
```

程序会自动创建：

```text
output/
```

目录。

---

# 输出文件

## test_detail.csv

所有测试结果。

字段：

| 字段 |
|--------|
| domain |
| source |
| api_score |
| api_latency |
| api_loss |
| tested_ip |
| success |
| colo |
| ttfb |

示例：

```csv
domain,source,tested_ip,success,colo,ttfb
cf.tencentapp.cn,static,104.16.1.1,True,HKG,0.021
```

---

## domain_rank.csv

域名汇总统计。

字段：

| 字段 |
|--------|
| domain |
| source |
| success_rate |
| avg_ttfb |
| total |
| success |
| fail |
| api_score |
| api_latency |
| api_loss |
| best_ttfb |

示例：

```csv
domain,success_rate,avg_ttfb
cf.tencentapp.cn,100,0.021
```

---

# 排序规则

优先：

```text
成功率高
```

其次：

```text
平均TTFB低
```

代码：

```python
(
    -success_rate,
    avg_ttfb
)
```

---

# 控制台输出

运行结束后自动输出：

```text
失败率最高域名
```

例如：

```text
store.ubi.com
```

---

```text
100%成功且最快域名
```

例如：

```text
cf.tencentapp.cn
```

---

```text
TOP10排行榜
```

例如：

```text
1. cf.tencentapp.cn
2. time.is
3. cf.blogluo.eu.org
...
```

---

# 注意事项

某些域名可能：

```text
禁止直接访问
启用了安全策略
已不在Cloudflare
```

此时可能全部失败。

属于正常情况。

---

# License

MIT License

# Cloudflare Domain Finder

用于从一组 Cloudflare 优选域名中：

1. DNS解析所有A记录
2. 提取关联IP
3. 使用指定目标域名进行回源测试
4. 统计成功率
5. 统计失败率
6. 计算平均TTFB
7. 自动找出：

- 失败率最高域名
- 100%成功且最快域名
- TOP10最佳域名

---

## 工作流程

例如：

候选域名：

```text
cf.tencentapp.cn
time.is
www.shopify.com
```

解析：

```text
cf.tencentapp.cn
├── 104.16.1.1
├── 104.16.1.2

time.is
├── 172.67.xx.xx
├── 104.22.xx.xx
```

然后使用：

```bash
curl \
--resolve monitor.example.com:443:104.16.1.1 \
https://monitor.example.com/cdn-cgi/trace
```

测试目标域名是否能够正常接入这些IP。

---

## 环境要求

### Linux

推荐：

- Ubuntu 22.04+
- Debian 11+
- CentOS Stream 9

### Python

```bash
Python >= 3.10
```

### 系统依赖

需要安装：

```bash
curl
dig
```

Ubuntu：

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

---

## 安装

克隆项目：

```bash
git clone https://github.com/yourname/cf-domain-finder.git

cd cf-domain-finder
```

安装依赖：

```bash
pip install -r requirements.txt
```

---

## 配置

编辑：

```python
config.py
```

修改目标域名：

```python
TARGET_DOMAIN = "monitor.example.com"
```

---

## 运行

```bash
python main.py
```

---

## 输出

### 明细

```text
output/cf_test_detail.csv
```

字段：

| 字段 |
|--------|
| source_domain |
| ip |
| success |
| colo |
| ttfb |

---

### 汇总

```text
output/cf_domain_rank.csv
```

字段：

| 字段 |
|--------|
| domain |
| total_ips |
| success_ips |
| fail_ips |
| success_rate |
| avg_ttfb |

---

## 示例输出

```text
================================================================================
100%成功且最快
================================================================================

cf.tencentapp.cn

总IP: 9
成功: 9

平均TTFB:
0.021s
```

---

## 排序逻辑

优先级：

1. 成功率高
2. 失败率低
3. 平均TTFB低

即：

```python
(-success_rate, avg_ttfb)
```

---

## License

MIT License

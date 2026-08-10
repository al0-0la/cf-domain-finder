import asyncio
import csv
from collections import defaultdict
import os
from config import *
from api import *


def parse_trace(text):

    result = {}

    for line in text.splitlines():

        if "=" not in line:
            continue

        k, v = line.split("=", 1)

        result[k] = v

    return result


async def test_ip(
    source_domain,
    meta,
    ip,
    sem
):

    async with sem:

        try:

            cmd = [
                "curl",
                "-s",
                "-o",
                "-",
                "-w",
                "\n__TTFB__:%{time_starttransfer}",

                "--connect-timeout",
                str(CONNECT_TIMEOUT),

                "--max-time",
                str(MAX_TIME),

                "--resolve",
                f"{TARGET_DOMAIN}:443:{ip}",

                f"https://{TARGET_DOMAIN}/cdn-cgi/trace"
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, _ = await proc.communicate()

            output = stdout.decode(
                errors="ignore"
            )

            if "__TTFB__:" not in output:

                return {
                    **meta,
                    "tested_ip": ip,
                    "success": False,
                    "colo": "",
                    "ttfb": ""
                }

            trace_text, ttfb_text = output.rsplit(
                "__TTFB__:",
                1
            )

            trace = parse_trace(
                trace_text
            )

            colo = trace.get(
                "colo"
            )

            if not colo:

                return {
                    **meta,
                    "tested_ip": ip,
                    "success": False,
                    "colo": "",
                    "ttfb": ""
                }

            return {
                **meta,
                "tested_ip": ip,
                "success": True,
                "colo": colo,
                "ttfb": float(ttfb_text.strip())
            }

        except Exception:

            return {
                **meta,
                "tested_ip": ip,
                "success": False,
                "colo": "",
                "ttfb": ""
            }


async def main():
    os.makedirs("output", exist_ok=True)
    domains = get_candidate_domains()

    print(
        f"获取域名数量: {len(domains)}"
    )

    sem = asyncio.Semaphore(
        MAX_CONCURRENT
    )

    tasks = []

    print("DNS解析...")

    for item in domains:

        dns_ips = await resolve_domain(
            item["domain"]
        )

        for ip in dns_ips:

            tasks.append(
                test_ip(
                    item["domain"],
                    item,
                    ip,
                    sem
                )
            )

    print(
        f"开始测试 {len(tasks)} 个IP"
    )

    results = []

    for task in asyncio.as_completed(tasks):

        result = await task

        results.append(result)

        if result["success"]:

            print(
                f"[OK] "
                f"{result['domain']} "
                f"{result['tested_ip']} "
                f"{result['colo']} "
                f"{result['ttfb']}"
            )

    #
    # Detail CSV
    #

    with open(
        "output/test_detail.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "domain",
            "source",
            "api_score",
            "api_latency",
            "api_loss",
            "tested_ip",
            "success",
            "colo",
            "ttfb"
        ])

        for r in results:

            writer.writerow([
                r["domain"],
                r["source"],
                r["avgScore"],
                r["avgLatency"],
                r["avgLoss"],
                r["tested_ip"],
                r["success"],
                r["colo"],
                r["ttfb"],
            ])

    #
    # 汇总
    #

    stat = defaultdict(
        lambda: {
            "source": "",
            "score": None,
            "latency": None,
            "loss": None,

            "total": 0,
            "success": 0,
            "fail": 0,

            "ttfb_sum": 0,
            "best_ttfb": 999
        }
    )

    for r in results:

        row = stat[r["domain"]]

        row["source"] = r["source"]
        row["score"] = r["avgScore"]
        row["latency"] = r["avgLatency"]
        row["loss"] = r["avgLoss"]

        row["total"] += 1

        if r["success"]:

            row["success"] += 1

            row["ttfb_sum"] += r["ttfb"]

            row["best_ttfb"] = min(
                row["best_ttfb"],
                r["ttfb"]
            )

        else:

            row["fail"] += 1

    ranks = []

    for domain, s in stat.items():

        success_rate = (
            s["success"] /
            s["total"] * 100
            if s["total"]
            else 0
        )

        avg_ttfb = (
            s["ttfb_sum"] /
            s["success"]
            if s["success"]
            else 999
        )

        ranks.append({
            "domain": domain,
            "source": s["source"],
            "success_rate": round(
                success_rate,
                2
            ),
            "avg_ttfb": round(
                avg_ttfb,
                4
            ),
            "total": s["total"],
            "success": s["success"],
            "fail": s["fail"],
            "api_score": s["score"],
            "api_latency": s["latency"],
            "api_loss": s["loss"],
            "best_ttfb": (
                round(
                    s["best_ttfb"],
                    4
                )
                if s["best_ttfb"] != 999
                else ""
            )
        })

    ranks.sort(
        key=lambda x: (
            -x["success_rate"],
            x["avg_ttfb"]
        )
    )

    with open(
        "output/domain_rank.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=ranks[0].keys()
        )

        writer.writeheader()

        writer.writerows(
            ranks
        )

    #
    # 输出结果
    #

    fail_worst = max(
        ranks,
        key=lambda x: x["fail"]
    )

    perfect = [
        x
        for x in ranks
        if x["fail"] == 0
        and x["success"] > 0
    ]

    print()

    print("=" * 60)
    print("失败率最高域名")
    print("=" * 60)

    print(fail_worst)

    print()

    print("=" * 60)
    print("100%成功且最快")
    print("=" * 60)

    if perfect:

        best = min(
            perfect,
            key=lambda x: x["avg_ttfb"]
        )

        print(best)

    print()

    print("=" * 60)
    print("TOP10")
    print("=" * 60)

    for row in ranks[:10]:

        print(
            row["domain"],
            row["success_rate"],
            row["avg_ttfb"]
        )


if __name__ == "__main__":

    asyncio.run(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import csv
import socket
from collections import defaultdict

TARGET_DOMAIN = "monitor.example.com"

cf_select_doma = [
    "cf.tencentapp.cn",
    "cf.468123.xyz",
    "cf.090227.xyz",
    "cf.877774.xyz",
    "cf.130519.xyz",
    "cf.008500.xyz",
    "saas.sin.fan",
    "cf.3666888.xyz"
]

cf_office_doma = [
    "icook.hk",
    "time.is",
    "staticdelivery.nexusmods.com",
    "store.ubi.com",
    "www.shopify.com",
    "mfa.gov.ua",
    "www.visa.cn"
]

MAX_CONCURRENT = 300

DETAIL_CSV = "cf_test_detail.csv"
SUMMARY_CSV = "cf_domain_rank.csv"


async def resolve_domain(domain):
    """
    获取域名所有A记录
    """

    try:
        proc = await asyncio.create_subprocess_exec(
            "dig",
            "+short",
            domain,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, _ = await proc.communicate()

        ips = []

        for line in stdout.decode().splitlines():

            line = line.strip()

            try:
                socket.inet_aton(line)
                ips.append(line)
            except Exception:
                pass

        return domain, ips

    except Exception:
        return domain, []


def parse_trace(text):

    data = {}

    for line in text.splitlines():

        if "=" not in line:
            continue

        k, v = line.split("=", 1)

        data[k.strip()] = v.strip()

    return data


async def test_ip(ip, source_domain, sem):

    async with sem:

        try:

            cmd = [
                "curl",
                "-s",
                "-o", "-",
                "-w", "\n__TTFB__:%{time_starttransfer}",
                "--connect-timeout", "5",
                "--max-time", "10",
                "--resolve",
                f"{TARGET_DOMAIN}:443:{ip}",
                f"https://{TARGET_DOMAIN}/cdn-cgi/trace"
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                return {
                    "source_domain": source_domain,
                    "ip": ip,
                    "success": False,
                    "colo": "",
                    "ttfb": ""
                }

            output = stdout.decode(errors="ignore")

            if "__TTFB__:" not in output:
                return {
                    "source_domain": source_domain,
                    "ip": ip,
                    "success": False,
                    "colo": "",
                    "ttfb": ""
                }

            trace_text, ttfb_text = output.rsplit(
                "__TTFB__:",
                1
            )

            trace = parse_trace(trace_text)

            colo = trace.get("colo")

            if not colo:
                return {
                    "source_domain": source_domain,
                    "ip": ip,
                    "success": False,
                    "colo": "",
                    "ttfb": ""
                }

            return {
                "source_domain": source_domain,
                "ip": ip,
                "success": True,
                "colo": colo,
                "ttfb": float(ttfb_text.strip())
            }

        except Exception:

            return {
                "source_domain": source_domain,
                "ip": ip,
                "success": False,
                "colo": "",
                "ttfb": ""
            }


async def main():

    domains = list(
        dict.fromkeys(
            cf_select_doma +
            cf_office_doma
        )
    )

    print(
        f"\n开始解析域名，共 {len(domains)} 个\n"
    )

    domain_ip_map = {}

    resolve_tasks = [
        resolve_domain(domain)
        for domain in domains
    ]

    for task in asyncio.as_completed(resolve_tasks):

        domain, ips = await task

        domain_ip_map[domain] = ips

        print(
            f"[DNS] "
            f"{domain:<40}"
            f"{len(ips)} IP"
        )

    print("\n开始测试...\n")

    sem = asyncio.Semaphore(MAX_CONCURRENT)

    tasks = []

    for domain, ips in domain_ip_map.items():

        for ip in ips:

            tasks.append(
                test_ip(
                    ip,
                    domain,
                    sem
                )
            )

    detail_results = []

    for future in asyncio.as_completed(tasks):

        result = await future

        detail_results.append(result)

        status = "OK" if result["success"] else "FAIL"

        print(
            f"[{status}] "
            f"{result['source_domain']:<35}"
            f"{result['ip']:<16}"
            f"{str(result['colo']):<8}"
            f"{str(result['ttfb'])}"
        )

    # =========================
    # 保存详细CSV
    # =========================

    with open(
        DETAIL_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "source_domain",
            "ip",
            "success",
            "colo",
            "ttfb"
        ])

        for row in detail_results:

            writer.writerow([
                row["source_domain"],
                row["ip"],
                row["success"],
                row["colo"],
                row["ttfb"]
            ])

    # =========================
    # 统计
    # =========================

    stats = defaultdict(lambda: {
        "total": 0,
        "success": 0,
        "fail": 0,
        "ttfb_sum": 0.0
    })

    for row in detail_results:

        domain = row["source_domain"]

        stats[domain]["total"] += 1

        if row["success"]:

            stats[domain]["success"] += 1
            stats[domain]["ttfb_sum"] += row["ttfb"]

        else:

            stats[domain]["fail"] += 1

    summary_rows = []

    for domain, s in stats.items():

        total = s["total"]

        success = s["success"]

        fail = s["fail"]

        success_rate = (
            success / total * 100
            if total else 0
        )

        avg_ttfb = (
            s["ttfb_sum"] / success
            if success else 999
        )

        summary_rows.append({
            "domain": domain,
            "total_ips": total,
            "success_ips": success,
            "fail_ips": fail,
            "success_rate": round(success_rate, 2),
            "avg_ttfb": round(avg_ttfb, 4)
        })

    summary_rows.sort(
        key=lambda x: (
            -x["success_rate"],
            x["avg_ttfb"]
        )
    )

    with open(
        SUMMARY_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "domain",
            "total_ips",
            "success_ips",
            "fail_ips",
            "success_rate",
            "avg_ttfb"
        ])

        for row in summary_rows:

            writer.writerow([
                row["domain"],
                row["total_ips"],
                row["success_ips"],
                row["fail_ips"],
                row["success_rate"],
                row["avg_ttfb"]
            ])

    # =========================
    # 失败率最高
    # =========================

    highest_fail = max(
        summary_rows,
        key=lambda x: x["fail_ips"]
    )

    # =========================
    # 100%成功且最快
    # =========================

    perfect_domains = [
        x
        for x in summary_rows
        if x["fail_ips"] == 0
        and x["success_ips"] > 0
    ]

    best_perfect = None

    if perfect_domains:

        best_perfect = min(
            perfect_domains,
            key=lambda x: x["avg_ttfb"]
        )

    print("\n")
    print("=" * 80)
    print("失败率最高域名")
    print("=" * 80)

    print(
        f"{highest_fail['domain']}\n"
        f"总IP: {highest_fail['total_ips']}\n"
        f"成功: {highest_fail['success_ips']}\n"
        f"失败: {highest_fail['fail_ips']}\n"
        f"成功率: {highest_fail['success_rate']}%"
    )

    print("\n")
    print("=" * 80)
    print("100%成功且最快")
    print("=" * 80)

    if best_perfect:

        print(
            f"{best_perfect['domain']}\n"
            f"总IP: {best_perfect['total_ips']}\n"
            f"平均TTFB: {best_perfect['avg_ttfb']}s"
        )

    else:

        print("没有100%成功的域名")

    print("\n")
    print("=" * 80)
    print("TOP10")
    print("=" * 80)

    for row in summary_rows[:10]:

        print(
            f"{row['domain']:<35}"
            f"成功率:{row['success_rate']:>6}%  "
            f"平均TTFB:{row['avg_ttfb']}s"
        )

    print("\n生成文件:")
    print(f"  {DETAIL_CSV}")
    print(f"  {SUMMARY_CSV}")


if __name__ == "__main__":
    asyncio.run(main())

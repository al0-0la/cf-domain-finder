import requests
import asyncio
import socket

from config import API_URL
from config import STATIC_DOMAINS


def get_candidate_domains():

    domains = {}

    #
    # 静态域名
    #

    for domain in STATIC_DOMAINS:

        domains[domain] = {
            "domain": domain,
            "source": "static",
            "avgScore": None,
            "avgLatency": None,
            "avgLoss": None,
        }

    #
    # VPS789
    #

    try:

        response = requests.get(
            API_URL,
            timeout=10
        )

        response.raise_for_status()

        goods = (
            response.json()
            .get("data", {})
            .get("good", [])
        )

        for item in goods:

            domain = item.get("ip")

            if not domain:
                continue

            domains[domain] = {
                "domain": domain,
                "source": "vps789",
                "avgScore": item.get("avgScore"),
                "avgLatency": item.get("avgLatency"),
                "avgLoss": item.get("avgPkgLostRate"),
            }

    except Exception as e:

        print(
            f"[API ERROR] {e}"
        )

    return list(domains.values())


async def resolve_domain(domain):

    try:

        proc = await asyncio.create_subprocess_exec(
            "dig",
            "+short",
            domain,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, _ = await proc.communicate()

        ips = []

        for line in stdout.decode().splitlines():

            ip = line.strip()

            try:

                socket.inet_aton(ip)

                ips.append(ip)

            except Exception:

                pass

        return ips

    except Exception:

        return []

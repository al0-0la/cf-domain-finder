import requests

from config import API_URL


def fetch_vps789_domains():

    try:

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            API_URL,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        goods = data.get("data", {}).get("good", [])

        domains = []

        for item in goods:

            domain = (
                item.get("domain")
                or item.get("host")
                or item.get("hostname")
            )

            if domain:
                domains.append(domain)

        return list(set(domains))

    except Exception as e:

        print(
            f"[API] VPS789获取失败: {e}"
        )

        return []

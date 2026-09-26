import json
import sys
from typing import Optional

import requests


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main():
    if len(sys.argv) < 3:
        print("Usage: python tools/shop_smoke.py <base_url> <token> [steam_id]")
        print("Example: python tools/shop_smoke.py http://127.0.0.1:3000 <JWT> 7656119...")
        sys.exit(2)

    base_url = sys.argv[1].rstrip("/")
    token = sys.argv[2]
    steam_id: Optional[str] = sys.argv[3] if len(sys.argv) >= 4 else None

    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    s.headers.update(_auth_header(token))

    if steam_id:
        print("[1] time tick")
        r = s.post(f"{base_url}/api/shop/rewards/time-tick", json={"steam_id": steam_id}, timeout=20)
        print(r.status_code, r.text)

    print("[2] admin credit idempotency")
    credit_body = {
        "external_id": "SMOKE_PIX_0001",
        "steam_id": steam_id or "76561198000000000",
        "amount": 10,
        "meta": {"note": "smoke"},
    }
    r1 = s.post(f"{base_url}/api/shop/admin/credit", json=credit_body, timeout=20)
    print(r1.status_code, r1.text)
    r2 = s.post(f"{base_url}/api/shop/admin/credit", json=credit_body, timeout=20)
    print(r2.status_code, r2.text)

    print("[3] delivery run (admin)")
    r = s.post(f"{base_url}/api/shop/delivery/run", json={"limit": 10}, timeout=60)
    print(r.status_code, r.text)


if __name__ == "__main__":
    main()

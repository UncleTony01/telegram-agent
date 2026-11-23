"""Buy one Reality Check from the x402 API with a test wallet, to prove payments work.

    .venv/bin/python scripts/x402_pay_test.py http://127.0.0.1:8402 "AVAX 100B"

The payer key is read from ~/.x402/payer.json (created on first run, chmod 600).
On Base Sepolia it needs test USDC only (no ETH: the facilitator pays the gas).
Get test USDC free at https://faucet.circle.com (choose Base Sepolia).
A spend cap of $0.05 per payment stops it from ever paying more than expected.
"""
import asyncio
import base64
import json
import os
import sys
from pathlib import Path

from eth_account import Account

KEY_FILE = Path(os.path.expanduser("~/.x402/payer.json"))


def payer() -> Account:
    if not KEY_FILE.exists():
        KEY_FILE.parent.mkdir(mode=0o700, exist_ok=True)
        acct = Account.create()
        fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(fd, json.dumps({"address": acct.address, "private_key": acct.key.hex(),
                                 "note": "Base Sepolia TEST wallet that pays the x402 API"}).encode())
        os.close(fd)
        print(f"Created test payer wallet {acct.address}. Fund it with test USDC, then run again.")
    return Account.from_key(json.loads(KEY_FILE.read_text())["private_key"])


async def main(base: str, claim: str) -> None:
    from x402 import x402Client, x402ClientConfig, SchemeRegistration
    from x402.http.clients import wrapHttpxWithPayment
    from x402.mechanisms.evm import EthAccountSigner
    from x402.mechanisms.evm.exact import ExactEvmScheme

    acct = payer()
    print("payer:", acct.address)
    client = x402Client.from_config(x402ClientConfig(
        schemes=[SchemeRegistration(network="eip155:*", client=ExactEvmScheme(signer=EthAccountSigner(acct)))],
        spend_controls={"max_amount_per_payment": "$0.05"},
    ))
    async with wrapHttpxWithPayment(client, timeout=60) as http:
        r = await http.get(f"{base.rstrip('/')}/check", params={"claim": claim})
    print("status:", r.status_code)
    receipt = r.headers.get("payment-response")
    if receipt:
        print("receipt:", json.dumps(json.loads(base64.b64decode(receipt)), indent=2))
    try:
        body = r.json()
        print(body.get("summary") or json.dumps(body, indent=2))
    except Exception:
        print(r.text[:500])


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8402",
                     sys.argv[2] if len(sys.argv) > 2 else "AVAX 100B"))

"""Trigger a server-side script run in the DEPLOYED Streamlit app by opening its
Streamlit websocket with a Databricks OAuth bearer token (the Apps OAuth proxy
accepts it), then sending a rerun BackMsg. With FEBAR_APP_SELFTEST=1 the app runs
one real enrichment on startup and persists it to Lakebase as the app service
principal — which we then verify externally.

Run:  PYTHONPATH=. python3 scripts/trigger_app_selftest.py
"""
from __future__ import annotations

import asyncio
import json
import ssl
import subprocess

import certifi
import websockets
from streamlit.proto.BackMsg_pb2 import BackMsg

_SSL = ssl.create_default_context(cafile=certifi.where())

APP_HOST = "febar-enrichment-app-7474646684279456.aws.databricksapps.com"
WS_URL = f"wss://{APP_HOST}/_stcore/stream"


def _token() -> str:
    out = subprocess.run(["databricks", "auth", "token", "--profile", "fevm"],
                         capture_output=True, text=True)
    return json.loads(out.stdout)["access_token"]


async def drive():
    token = _token()
    headers = {"Authorization": f"Bearer {token}"}
    async with websockets.connect(WS_URL, additional_headers=headers,
                                  max_size=None, open_timeout=30, ssl=_SSL) as ws:
        # request an initial script run
        msg = BackMsg()
        try:
            msg.rerun_script.query_string = ""
        except Exception:
            pass
        await ws.send(msg.SerializeToString())
        # keep the session open long enough for the server to run enrichment
        got = 0
        try:
            while got < 40:
                await asyncio.wait_for(ws.recv(), timeout=25)
                got += 1
        except asyncio.TimeoutError:
            pass
        print(f"received {got} ForwardMsg frames from the app session")


if __name__ == "__main__":
    asyncio.run(drive())
    print("done")

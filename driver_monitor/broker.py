from __future__ import annotations

import asyncio


async def _serve(host: str, port: int) -> None:
    from amqtt.broker import Broker

    config = {
        "listeners": {"default": {"type": "tcp", "bind": f"{host}:{port}"}},
        "plugins": {
            "amqtt.plugins.authentication.AnonymousAuthPlugin": {
                "allow_anonymous": True
            }
        },
    }
    broker = Broker(config)
    await broker.start()
    print(f"MQTT broker ready at {host}:{port}", flush=True)
    try:
        await asyncio.Event().wait()
    finally:
        await broker.shutdown()


def run_broker(host: str = "0.0.0.0", port: int = 1883) -> None:
    try:
        asyncio.run(_serve(host, port))
    except KeyboardInterrupt:
        print("\nMQTT broker stopped.")

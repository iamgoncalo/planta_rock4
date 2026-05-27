"""
PlantaOS RIR 2026 — MQTT Bridge
Subscribes to ALL device topics → caches state → allows sending commands.
Does NOT depend on the WebSocket manager (terminal WS polls device_cache directly).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

log = logging.getLogger("mqtt_bridge")

# Live device state cache — latest known payload per cluster per channel
device_cache: dict[str, dict[str, Any]] = {}

# Subscribers that want to be notified of new MQTT messages (for live terminal forwarding)
_subscribers: list[asyncio.Queue] = []


def subscribe() -> asyncio.Queue:
    """Register a queue to receive (cluster_id, channel, payload) tuples."""
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue) -> None:
    try:
        _subscribers.remove(q)
    except ValueError:
        pass


async def _notify(cluster_id: str | None, channel: str, payload: Any) -> None:
    msg = {"cluster_id": cluster_id, "channel": channel, "payload": payload, "ts": time.time()}
    for q in list(_subscribers):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass


async def mqtt_bridge_loop() -> None:
    """
    Runs forever inside the FastAPI lifespan.
    Reconnects on error.  Requires 'aiomqtt' package.
    """
    try:
        import aiomqtt
    except ImportError:
        log.error("aiomqtt not installed — run: pip install aiomqtt")
        return

    from app.config import get_settings
    s = get_settings()

    while True:
        try:
            async with aiomqtt.Client(
                hostname=s.mqtt_host,
                port=s.mqtt_port,
                username=s.mqtt_user,
                password=s.mqtt_password,
            ) as client:
                log.info("mqtt.connected host=%s port=%d", s.mqtt_host, s.mqtt_port)

                await client.subscribe("planta/wc/+/telemetry")
                await client.subscribe("planta/wc/+/status")
                await client.subscribe("planta/wc/+/response")
                await client.subscribe("planta/wc/+/event")
                await client.subscribe("planta/wc/+/serial")
                await client.subscribe("planta/system/online")

                async for msg in client.messages:
                    topic   = str(msg.topic)
                    payload_raw = msg.payload.decode("utf-8", errors="replace")
                    parts   = topic.split("/")

                    cluster_id: str | None
                    if len(parts) >= 4:
                        cluster_id = parts[2]
                        channel    = parts[3]
                    elif topic == "planta/system/online":
                        cluster_id = None
                        channel    = "online"
                    else:
                        continue

                    # Parse JSON or keep as string (serial is plain text)
                    try:
                        data: Any = json.loads(payload_raw)
                    except json.JSONDecodeError:
                        data = payload_raw

                    # Update in-memory cache
                    if cluster_id:
                        if cluster_id not in device_cache:
                            device_cache[cluster_id] = {}
                        device_cache[cluster_id][channel]     = data
                        device_cache[cluster_id]["last_seen"] = time.time()
                        if channel == "serial":
                            device_cache[cluster_id]["last_serial"] = payload_raw

                    await _notify(cluster_id, channel, data)

        except Exception as e:  # aiomqtt.MqttError or network error
            log.warning("mqtt.disconnected err=%s — retry in 5s", e)
            await asyncio.sleep(5)


async def send_command(cluster_id: str, cmd: dict) -> bool:
    """Publish a command to a single device. Returns True on success."""
    try:
        import aiomqtt
        from app.config import get_settings
        s = get_settings()
        async with aiomqtt.Client(
            hostname=s.mqtt_host,
            port=s.mqtt_port,
            username=s.mqtt_user,
            password=s.mqtt_password,
        ) as client:
            topic   = f"planta/wc/{cluster_id}/cmd"
            payload = json.dumps(cmd)
            await client.publish(topic, payload, qos=1)
            log.info("cmd.sent cluster=%s cmd=%s", cluster_id, cmd.get("cmd"))
            return True
    except Exception as e:
        log.error("cmd.failed cluster=%s err=%s", cluster_id, e)
        return False


async def broadcast_command(cmd: dict) -> bool:
    """Publish a command to ALL devices via the broadcast topic."""
    try:
        import aiomqtt
        from app.config import get_settings
        s = get_settings()
        async with aiomqtt.Client(
            hostname=s.mqtt_host,
            port=s.mqtt_port,
            username=s.mqtt_user,
            password=s.mqtt_password,
        ) as client:
            await client.publish("planta/system/broadcast", json.dumps(cmd), qos=1)
            log.info("broadcast.sent cmd=%s", cmd.get("cmd"))
            return True
    except Exception as e:
        log.error("broadcast.failed err=%s", e)
        return False


def get_device_status(cluster_id: str) -> dict:
    """Latest known state for a cluster, derived from MQTT cache."""
    cached = device_cache.get(cluster_id, {})
    last_seen = cached.get("last_seen")
    age_s     = round(time.time() - last_seen) if last_seen else None

    if age_s is None:
        status = "unknown"
    elif age_s < 15:
        status = "online"
    elif age_s < 60:
        status = "degraded"
    else:
        status = "offline"

    status_payload: dict = cached.get("status", {})
    return {
        "cluster_id":   cluster_id,
        "status":       status,
        "age_s":        age_s,
        "last_seen_ts": last_seen,
        **{k: v for k, v in status_payload.items()
           if k not in ("cluster_id", "ts")},
    }


def get_all_device_statuses() -> list[dict]:
    clusters = ["WC-01", "WC-02", "WC-03", "WC-04",
                "WC-05", "WC-06", "WC-07", "WC-08"]
    return [get_device_status(c) for c in clusters]

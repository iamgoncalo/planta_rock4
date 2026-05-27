#!/usr/bin/env python3
"""
PlantaOS RIR 2026 — Serial Bridge
Bridges USB serial (LilyGo) ↔ MQTT broker.
Lets you see Arduino Serial Monitor output in the browser terminal.

Usage:
  python3 serial_bridge.py --port /dev/ttyUSB0 --cluster WC-01
  python3 serial_bridge.py --port COM3 --cluster WC-01   (Windows)

Requires: pip install pyserial paho-mqtt
"""
import argparse
import json
import time
import serial
import paho.mqtt.client as mqtt


def main() -> None:
    ap = argparse.ArgumentParser(description="PlantaOS Serial Bridge — USB ↔ MQTT")
    ap.add_argument("--port",    required=True, help="Serial port, ex: /dev/ttyUSB0 or COM3")
    ap.add_argument("--cluster", required=True, help="Cluster ID, ex: WC-01")
    ap.add_argument("--baud",    default=115200, type=int, help="Baud rate (default 115200)")
    ap.add_argument("--broker",  default="localhost", help="MQTT broker hostname")
    ap.add_argument("--mport",   default=1883, type=int, help="MQTT broker port")
    ap.add_argument("--user",    default="plantaos", help="MQTT username")
    ap.add_argument("--passwd",  default="planta2026mqtt", help="MQTT password")
    args = ap.parse_args()

    print(f"[bridge] {args.port} @ {args.baud}bps → MQTT {args.broker}:{args.mport}")
    print(f"[bridge] Cluster: {args.cluster}")
    print(f"[bridge] Ctrl+C para parar\n")

    topic_serial = f"planta/wc/{args.cluster}/serial"
    topic_cmd    = f"planta/wc/{args.cluster}/cmd"

    # MQTT setup
    mq = mqtt.Client(client_id=f"bridge_{args.cluster}")
    mq.username_pw_set(args.user, args.passwd)
    mq.connect(args.broker, args.mport)
    mq.loop_start()

    # Serial setup
    ser = serial.Serial(args.port, args.baud, timeout=1)
    print(f"[bridge] Porta serial aberta. A reencaminhar para {topic_serial}")

    # Commands from MQTT → serial
    def on_message(client, userdata, msg: mqtt.MQTTMessage) -> None:
        payload = msg.payload.decode("utf-8", errors="replace")
        print(f"[bridge] → serial: {payload}")
        ser.write((payload + "\n").encode("utf-8"))

    mq.subscribe(topic_cmd)
    mq.on_message = on_message

    # Serial output → MQTT
    buffer = ""
    try:
        while True:
            if ser.in_waiting:
                raw     = ser.read(ser.in_waiting).decode("utf-8", errors="replace")
                buffer += raw
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        print(f"[serial] {line}")
                        mq.publish(topic_serial, line, qos=0)
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n[bridge] Parado")
    finally:
        ser.close()
        mq.loop_stop()


if __name__ == "__main__":
    main()

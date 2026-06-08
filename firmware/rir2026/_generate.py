#!/usr/bin/env python3
"""Gera os 34 .ino para o festival Rock in Rio Lisboa 2026.
Uso: python3 firmware/rir2026/_generate.py
"""
import math, os, re

ANCHOR = {"lat": 38.78145, "lon": -9.09430}
M_LAT  = 111_320.0
M_LON  = 111_320.0 * math.cos(math.radians(ANCHOR["lat"]))

CLUSTERS_GEO = [
    {"id":"wc-01","e":215.2,"n":327.3,"mf":True, "cm":72,"cf":63},
    {"id":"wc-02","e":256.9,"n":286.1,"mf":True, "cm":54,"cf":72},
    {"id":"wc-03","e":268.2,"n":194.8,"mf":True, "cm":54,"cf":48},
    {"id":"wc-04","e":298.5,"n":288.3,"mf":True, "cm":84,"cf":66},
    {"id":"wc-05","e":274.2,"n":238.2,"mf":False,"cu":133},
    {"id":"wc-06","e":60.7, "n":82.4, "mf":False,"cu":208},
    {"id":"wc-07","e":228.2,"n":148.1,"mf":True, "cm":84,"cf":54},
    {"id":"wc-08","e":0.0,  "n":0.0,  "mf":True, "cm":84,"cf":61},
]

TEMPLATE = open(os.path.join(os.path.dirname(__file__), "_TEMPLATE.ino")).read()

def gps(e, n):
    lat = round(ANCHOR["lat"] + n / M_LAT, 6)
    lon = round(ANCHOR["lon"] + e / M_LON, 6)
    return lat, lon

def render(fields: dict) -> str:
    src = TEMPLATE
    for k, v in fields.items():
        src = src.replace("{{" + k + "}}", str(v))
    return src

OUT = os.path.dirname(__file__)
generated = []

for c in CLUSTERS_GEO:
    cid  = c["id"]
    num  = cid.split("-")[1]   # "01", "02", …
    lat, lon = gps(c["e"], c["n"])

    if c["mf"]:
        # 5 .ino por cluster M/F
        specs = [
            # (filename,         porta, secao, cap,    nome_curto,             usar_ir)
            (f"wc{num}_h_ll", "LL",  "m",   c["cm"], f"WC-{num} MASC LL", True),
            (f"wc{num}_h_lr", "LR",  "m",   c["cm"], f"WC-{num} MASC LR", True),
            (f"wc{num}_w_ll", "LL",  "f",   c["cf"], f"WC-{num} FEM LL",  True),
            (f"wc{num}_w_lr", "LR",  "f",   c["cf"], f"WC-{num} FEM LR",  True),
            (f"wc{num}_center","C",  "m",   c["cm"], f"WC-{num} CENTER",  False),
        ]
        for fname, porta, secao, cap, nome, usar_ir in specs:
            sec_upper = secao.upper()
            etiqueta  = f"WC-{num}_{sec_upper}_{porta}"
            fields = {
                "ETIQUETA":    etiqueta,
                "CLUSTER_ID":  cid,
                "NOME_CURTO":  nome,
                "PORTA":       porta,
                "SECAO":       secao,
                "CAPACIDADE":  cap,
                "LAT":         lat,
                "LON":         lon,
                "USAR_IR":     "true" if usar_ir else "false",
                "USAR_IR_DEF": "1" if usar_ir else "0",
                "USAR_IR_STR": '"sim"' if usar_ir else '"nao"',
            }
            path = os.path.join(OUT, fname + ".ino")
            open(path, "w").write(render(fields))
            generated.append(fname + ".ino")
    else:
        # 2 .ino por cluster unissexo
        cap = c["cu"]
        for tag in ("a", "b"):
            fname = f"wc{num}_{tag}"
            etiqueta = f"WC-{num}_U_{tag.upper()}"
            fields = {
                "ETIQUETA":    etiqueta,
                "CLUSTER_ID":  cid,
                "NOME_CURTO":  f"WC-{num} UNI {tag.upper()}",
                "PORTA":       "",
                "SECAO":       "u",
                "CAPACIDADE":  cap,
                "LAT":         lat,
                "LON":         lon,
                "USAR_IR":     "false",
                "USAR_IR_DEF": "0",
                "USAR_IR_STR": '"nao"',
            }
            path = os.path.join(OUT, fname + ".ino")
            open(path, "w").write(render(fields))
            generated.append(fname + ".ino")

print(f"Gerados {len(generated)} ficheiros:")
for f in generated:
    print(f"  {f}")

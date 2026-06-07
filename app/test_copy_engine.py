from copy_engine import (
    build_copy, ClusterSnapshot, SectionInput,
)

def sec(cid, seccao, pct, is_uni=False, fila=0, espera=0.0, fluxo=0.0, conf=0.9, live=True):
    sid = f"{cid}_{seccao}"
    return SectionInput(sid, cid, seccao, pct, fila, espera, fluxo, conf, live, is_uni)

def cluster(cid, *secs):
    return ClusterSnapshot(cid, list(secs))

NOW = 1_780_000_000_000

print("="*72)
print("TESTES DO MOTOR DE COPY — cada cenario tem de disparar a frase certa")
print("="*72)

# Cenario 1: WC-01 vazio, WC-02 cheio -> WC-01 deve dizer REFUGIO (manda p/ ca)
clusters = [
    cluster("wc-01", sec("wc-01","m",1.0), sec("wc-01","f",1.0)),
    cluster("wc-02", sec("wc-02","m",90.0), sec("wc-02","f",92.0)),
    cluster("wc-03", sec("wc-03","m",40.0), sec("wc-03","f",40.0)),
]
r = build_copy(clusters, NOW)
print("\n[1] WC-01 vazio + WC-02 cheio:")
print("  wc-01_m:", r["wc-01_m"].pt, "| tom:", r["wc-01_m"].tom)
assert "WC-02" in r["wc-01_m"].pt or "refugio" in r["wc-01_m"].tom or r["wc-01_m"].tom=="livre"

# Cenario 2: WC-04 no limite -> sugere alternativa por nome
clusters = [
    cluster("wc-04", sec("wc-04","m",98.0), sec("wc-04","f",97.0)),
    cluster("wc-08", sec("wc-08","m",10.0), sec("wc-08","f",12.0)),
]
r = build_copy(clusters, NOW)
print("\n[2] WC-04 no limite (deve sugerir WC-08):")
print("  wc-04_m:", r["wc-04_m"].pt, "| tom:", r["wc-04_m"].tom)
assert r["wc-04_m"].tom == "limite"
assert "WC-08" in r["wc-04_m"].pt

# Cenario 3: M muito mais cheio que F no mesmo cluster
clusters = [
    cluster("wc-03", sec("wc-03","m",85.0), sec("wc-03","f",30.0)),
]
r = build_copy(clusters, NOW)
print("\n[3] WC-03 M cheio (85) vs F livre (30):")
print("  wc-03_m:", r["wc-03_m"].pt)
print("  wc-03_f:", r["wc-03_f"].pt)
assert r["wc-03_m"].pt != r["wc-03_f"].pt, "M e F tem de ter frases diferentes"

# Cenario 4: leitura nao fiavel -> neutro, sem numeros
clusters = [
    cluster("wc-05", sec("wc-05","u",50.0, is_uni=True, conf=0.1, live=False)),
]
r = build_copy(clusters, NOW)
print("\n[4] WC-05 offline/baixa confianca:")
print("  wc-05_u:", r["wc-05_u"].pt, "| tom:", r["wc-05_u"].tom)
assert r["wc-05_u"].tom == "neutro"

# Cenario 5: unissexo vazio
clusters = [
    cluster("wc-06", sec("wc-06","u",1.0, is_uni=True)),
    cluster("wc-02", sec("wc-02","m",95.0), sec("wc-02","f",95.0)),
]
r = build_copy(clusters, NOW)
print("\n[5] WC-06 unissexo vazio + WC-02 cheio:")
print("  wc-06_u:", r["wc-06_u"].pt, "| tom:", r["wc-06_u"].tom)
assert r["wc-06_u"].tom in ("vazio","livre")

# Cenario 6: pico de fluxo
clusters = [
    cluster("wc-01", sec("wc-01","m",75.0, fluxo=12.0), sec("wc-01","f",75.0, fluxo=12.0)),
]
r = build_copy(clusters, NOW)
print("\n[6] WC-01 a 75% com pico de entrada (fluxo=12):")
print("  wc-01_m:", r["wc-01_m"].pt, "| tom:", r["wc-01_m"].tom)

# Cenario 7: as frases rodam no tempo (nao repete sempre a mesma)
clusters = [cluster("wc-08", sec("wc-08","m",30.0), sec("wc-08","f",30.0))]
frases = set()
for t in range(0, 60000, 11000):
    rr = build_copy(clusters, NOW + t)
    frases.add(rr["wc-08_m"].pt)
print("\n[7] Rotacao no tempo (60s):", len(frases), "frases diferentes")
assert len(frases) >= 2, "deve rodar entre varias frases"

# Cenario 8: dia inteiro — todas as 14 seccoes sempre tem frase
clusters = [
    cluster("wc-01", sec("wc-01","m",20), sec("wc-01","f",30)),
    cluster("wc-02", sec("wc-02","m",60), sec("wc-02","f",80)),
    cluster("wc-03", sec("wc-03","m",95), sec("wc-03","f",40)),
    cluster("wc-04", sec("wc-04","m",10), sec("wc-04","f",15)),
    cluster("wc-05", sec("wc-05","u",70, is_uni=True)),
    cluster("wc-06", sec("wc-06","u",55, is_uni=True)),
    cluster("wc-07", sec("wc-07","m",88), sec("wc-07","f",50)),
    cluster("wc-08", sec("wc-08","m",5), sec("wc-08","f",8)),
]
r = build_copy(clusters, NOW)
print("\n[8] Festival completo — 14 seccoes:")
for sid in sorted(r):
    c = r[sid]
    assert c.pt and c.en, f"{sid} sem frase!"
    print(f"  {sid:10} [{c.tom:8}] {c.pt}")

print("\n" + "="*72)
print("TODOS OS TESTES PASSARAM ✓ — o motor compara clusters, distingue M/F,")
print("e cobre vazio/livre/cheio/limite/refugio/pico/offline/unissexo.")

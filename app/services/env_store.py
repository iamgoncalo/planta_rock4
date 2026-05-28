"""
PlantaOS — Store de AMBIENTES. Cada ambiente e um espaco de trabalho com a sua
frota, modo (sim|real) e cadencia. "rock-in-rio" e fixo (os 78). Os outros sao
criados pelo utilizador e guardados em memoria. Via B: lobby de sinais orfaos.
Thread-safe.
"""
from __future__ import annotations
import threading, time, re

_LOCK = threading.Lock()

# ambiente fixo do festival
ROCK_ENV = {
    "id": "rock-in-rio",
    "nome": "Rock in Rio Lisboa 2026",
    "modo": "sim",
    "refresh_ms": 6000,
    "fixo": True,
    "fonte": "registry",  # frota vem do sensors_registry (78)
}

# ambientes criados pelo utilizador: id -> dict
_ENVS: dict[str, dict] = {}
# sensores por ambiente: env_id -> [ {id,tipo,label,cluster} ]
_ENV_SENSORS: dict[str, list] = {}
# lobby (via B): sinais que chegaram sem ambiente. id -> {tipo,last_seen,sample}
_LOBBY: dict[str, dict] = {}

# ambientes-semente uteis para a demo (criados a primeira vez)
_SEEDED = False


def _slug(nome: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")
    return s or f"env-{int(time.time())}"


def _seed():
    global _SEEDED
    if _SEEDED:
        return
    _SEEDED = True
    # ambientes relacionados ao Rock in Rio, como pediste
    create_env("Teste de sensores", modo="real", refresh_ms=1500)
    create_env("Ver ao vivo", modo="real", refresh_ms=2000)


def list_envs() -> list[dict]:
    _seed()
    with _LOCK:
        out = [dict(ROCK_ENV)]
        for e in _ENVS.values():
            ee = dict(e)
            ee["n_sensores"] = len(_ENV_SENSORS.get(e["id"], []))
            out.append(ee)
        # contagem do rock
        out[0]["n_sensores"] = 78
        return out


def get_env(env_id: str) -> dict | None:
    _seed()
    if env_id == "rock-in-rio":
        e = dict(ROCK_ENV); e["n_sensores"] = 78; e["sensores"] = []  # frota via registry
        return e
    with _LOCK:
        e = _ENVS.get(env_id)
        if not e:
            return None
        ee = dict(e)
        ee["sensores"] = list(_ENV_SENSORS.get(env_id, []))
        ee["n_sensores"] = len(ee["sensores"])
        return ee


def create_env(nome: str, modo: str = "real", refresh_ms: int = 1500) -> dict:
    _seed()
    eid = _slug(nome)
    with _LOCK:
        # evitar colisao
        base = eid; i = 2
        while eid in _ENVS or eid == "rock-in-rio":
            eid = f"{base}-{i}"; i += 1
        env = {"id": eid, "nome": nome, "modo": modo if modo in ("sim","real") else "real",
               "refresh_ms": max(500, min(10000, int(refresh_ms))), "fixo": False, "fonte": "custom"}
        _ENVS[eid] = env
        _ENV_SENSORS[eid] = []
        return dict(env)


def delete_env(env_id: str) -> bool:
    if env_id == "rock-in-rio":
        return False
    with _LOCK:
        _ENVS.pop(env_id, None)
        _ENV_SENSORS.pop(env_id, None)
        return True


def add_sensor(env_id: str, sid: str, tipo: str, label: str = "", cluster: str = "") -> dict | None:
    if env_id == "rock-in-rio":
        return None  # frota fixa
    with _LOCK:
        if env_id not in _ENVS:
            return None
        lst = _ENV_SENSORS.setdefault(env_id, [])
        if any(s["id"] == sid for s in lst):
            return None  # ja existe
        sensor = {"id": sid, "tipo": tipo, "label": label or sid, "cluster": cluster or None}
        lst.append(sensor)
        # se veio do lobby, remove de la
        _LOBBY.pop(sid, None)
        return dict(sensor)


def remove_sensor(env_id: str, sid: str) -> bool:
    with _LOCK:
        lst = _ENV_SENSORS.get(env_id, [])
        n = len(lst)
        _ENV_SENSORS[env_id] = [s for s in lst if s["id"] != sid]
        return len(_ENV_SENSORS[env_id]) < n


def env_sensors(env_id: str) -> list:
    with _LOCK:
        return list(_ENV_SENSORS.get(env_id, []))


# ─── VIA B: lobby de descoberta ───
def lobby_signal(sid: str, tipo: str = "desconhecido", sample: dict | None = None):
    """Um sinal chegou sem ambiente. Regista no lobby (se nao pertence a nenhum env)."""
    with _LOCK:
        # se ja pertence a um ambiente, ignora
        for lst in _ENV_SENSORS.values():
            if any(s["id"] == sid for s in lst):
                return
        _LOBBY[sid] = {"id": sid, "tipo": tipo, "last_seen": time.time(), "sample": sample or {}}


def get_lobby(ttl_s: float = 120) -> list:
    now = time.time()
    with _LOCK:
        out = []
        for sid, info in list(_LOBBY.items()):
            age = now - info["last_seen"]
            if age > ttl_s:
                _LOBBY.pop(sid, None); continue
            out.append({**info, "age_s": round(age, 1)})
        return sorted(out, key=lambda x: x["last_seen"], reverse=True)


if __name__ == "__main__":
    print("=== AMBIENTES iniciais (semente) ===")
    for e in list_envs():
        print(f"  {e['id']}: '{e['nome']}' · modo={e['modo']} · {e['refresh_ms']}ms · {e['n_sensores']} sensores · {'fixo' if e.get('fixo') else 'custom'}")

    print("\n=== criar ambiente 'Bancada' ===")
    b = create_env("Bancada Porto", modo="real", refresh_ms=1000)
    print(f"  criado: {b['id']} · {b['refresh_ms']}ms")
    add_sensor(b["id"], "bancada-lilygo-1", "lilygo", "LilyGo de mesa")
    add_sensor(b["id"], "bancada-cam-1", "camera", "OAK teste")
    e = get_env(b["id"])
    print(f"  {e['id']}: {e['n_sensores']} sensores -> {[s['label'] for s in e['sensores']]}")

    print("\n=== VIA B: sinais orfaos no lobby ===")
    lobby_signal("lilygo-XYZ-99", "lilygo", {"pessoas": 12})
    lobby_signal("cam-novo-7", "camera", {"fps": 12})
    for s in get_lobby():
        print(f"  lobby: {s['id']} ({s['tipo']}) ha {s['age_s']}s")

    print("\n=== adotar do lobby para a Bancada ===")
    add_sensor(b["id"], "lilygo-XYZ-99", "lilygo", "adotado do lobby")
    print(f"  Bancada agora: {get_env(b['id'])['n_sensores']} sensores")
    print(f"  lobby restante: {len(get_lobby())}")

    print("\n=== rock-in-rio mantem-se fixo (78) e nao se apaga ===")
    print(f"  delete rock-in-rio: {delete_env('rock-in-rio')} (deve ser False)")
    print(f"  rock-in-rio sensores: {get_env('rock-in-rio')['n_sensores']}")

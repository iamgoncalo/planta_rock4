"""
PlantaOS — 25 CENÁRIOS DE OPERAÇÃO (S01..S25), um teste por cenário.

Cada cenário valida o comportamento de ponta-a-ponta do motor com as APIs
e módulos reais (fusão rolante, secções M/F, rota leve, ambiente, gateways,
históricos, decision_log). `pytest -k cenario` → 25 testes.

  S01 chuva muda espera + decision_log        S14 narrativa determinista <2.5 s
  S02 lama muda top-3 · PCD evita lama        S15 warm start pre==pos
  S03 chuva >60 min generaliza lama           S16 surto pós-headliner ×3.8
  S04 calor sobe procura_factor               S17 dois shows sobrepostos
  S05 evacuação em bloco                      S18 rampa de entrada sem anomalia
  S06 fechar cada cluster exclui-o do route   S19 modo saída muda o payload
  S07 limpeza F não afecta a irmã M           S20 congestão parado vs a fluir
  S08 regra steward WC-05                     S21 saturação → recusas >0
  S09 corte de aresta dá alternativa          S22 tempestade perfeita
  S10 blackout 10 min sem fontes              S23 memória entre dias (a fica)
  S11 gateway calado 3 min                    S24 quarentena de nó
  S12 remover 1 e 2 nós (mediana)             S25 ts_suspeito (relógio errado)
  S13 buffer local quando o Postgres cai
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.clusters_capacity import ALL_CLUSTERS
from app.clusters_geo import distance_m
from app.services import ambiente, gateways_hb, rota_leve, secoes_mf
from app.services import fusao_rolante as fr
from app.services import fusao_rolante_demo as demo
from app.services import node_calibration as nc

# Base temporal sintética (fora de qualquer janela de surto pós-show real)
T0 = 1_750_000_000.0
T0_MS = int(T0 * 1000)


@pytest.fixture(autouse=True)
def _estado_limpo():
    """Cada cenário parte de estado totalmente virgem (padrão da suite)."""
    from app.services import decision_log, section_history
    mods = (fr, nc, secoes_mf, section_history, decision_log, rota_leve,
            ambiente, gateways_hb)
    for mod in mods:
        mod.reset()
    yield
    for mod in mods:
        mod.reset()


def _show(end_delta_s: float, *, stage: str = "Palco Mundo",
          headliner: bool = True, show_id: str = "show_sintetico",
          base_s: float = T0):
    """Show sintético cujo fim é base_s + end_delta_s."""
    end_s = base_s + end_delta_s
    return SimpleNamespace(
        show_id=show_id, name="Sintético", stage=stage,
        start_iso=datetime.fromtimestamp(end_s - 5400.0,
                                         tz=timezone.utc).isoformat(),
        end_iso=datetime.fromtimestamp(end_s, tz=timezone.utc).isoformat(),
        headliner=headliner, expected_surge_pct=80.0,
    )


def _sem_nan(obj) -> bool:
    """True se nenhum número do payload (recursivo) é NaN/inf."""
    if isinstance(obj, dict):
        return all(_sem_nan(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return all(_sem_nan(v) for v in obj)
    if isinstance(obj, bool):
        return True
    if isinstance(obj, (int, float)):
        return math.isfinite(obj)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# S01 — chuva muda a espera e fica auditada
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s01():
    """Chuva activa: dwell ×1.4 ⇒ espera_prevista sobe ×1.4 + decision_log."""
    from app.services import decision_log
    fila = 30.0
    espera_antes = secoes_mf.espera_prevista_min("wc-03_f", fila)
    ambiente.set_flag("chuva", True, "matheus", intensidade="forte",
                      justificacao="aguaceiro real")
    espera_depois = secoes_mf.espera_prevista_min("wc-03_f", fila)
    assert espera_depois > espera_antes
    assert espera_depois / espera_antes == pytest.approx(1.4, rel=0.02)
    assert ambiente.dwell_factor() == pytest.approx(1.4)
    assert ambiente.procura_factor() == pytest.approx(1.2)
    regs = decision_log.query(tipo="ambiente_chuva")
    assert len(regs) == 1
    assert regs[0]["utilizador"] == "matheus"
    assert regs[0]["antes"]["activa"] is False
    assert regs[0]["depois"]["activa"] is True


# ─────────────────────────────────────────────────────────────────────────────
# S02 — lama muda o top-3 e PCD evita a aresta
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s02():
    """Lama nas saídas de WC-08: caminhada sobe no top-3; pcd NUNCA usa lama."""
    demo.demo_tick(T0)
    base = rota_leve.dijkstra_min("WC-08")
    r_sem = rota_leve.compute_route("WC-08", "f", now_s=T0)
    cam_sem = {o["wc"]: o["caminhada_min"] for o in r_sem["opcoes"]}

    ambiente.set_aresta_estado("WC-01|WC-08", "lama", "matheus", "poça")
    ambiente.set_aresta_estado("WC-06|WC-08", "lama", "matheus", "poça")
    rota_leve.reset()

    walk = rota_leve.dijkstra_min("WC-08")
    assert walk["WC-01"] > base["WC-01"]          # lama abranda a caminhada
    r_com = rota_leve.compute_route("WC-08", "f", now_s=T0 + 1.0)
    cam_com = {o["wc"]: o["caminhada_min"] for o in r_com["opcoes"]}
    comuns = set(cam_sem) & set(cam_com)
    assert all(cam_com[wc] >= cam_sem[wc] for wc in comuns)
    assert (any(cam_com[wc] > cam_sem[wc] for wc in comuns)
            or set(cam_sem) != set(cam_com))       # o top-3 mudou com a lama

    # PCD: excluir lama == cortar a aresta do grafo
    ambiente.set_aresta_estado("WC-06|WC-08", "normal", "matheus")
    ambiente.set_aresta_estado("WC-01|WC-08", "cortada", "matheus")
    d_sem_aresta = rota_leve.dijkstra_min("WC-08")["WC-01"]
    ambiente.set_aresta_estado("WC-01|WC-08", "lama", "matheus")
    walk_pcd = rota_leve.dijkstra_min("WC-08", pcd=True)
    assert walk_pcd["WC-01"] == pytest.approx(d_sem_aresta, abs=0.1)
    assert walk_pcd["WC-01"] > base["WC-01"]


# ─────────────────────────────────────────────────────────────────────────────
# S03 — chuva >60 min generaliza a lama (reversível)
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s03():
    """A chover há 70 min ⇒ lama em TODAS as arestas; pára ⇒ reverte."""
    ambiente.set_flag("chuva", True, "matheus")
    assert ambiente.lama_generalizada() is False
    with ambiente._LOCK:
        ambiente._ESTADO["chuva"]["desde_ts"] = time.time() - 70 * 60.0
    assert ambiente.lama_generalizada() is True
    assert ambiente.arestas_em_lama() == ambiente.arestas_validas()
    d = distance_m("WC-01", "WC-02")
    vel_lama = rota_leve.VELOCIDADE_M_MIN * ambiente.FACTOR_LAMA
    assert rota_leve.dijkstra_min("WC-01")["WC-02"] == pytest.approx(
        d / vel_lama, abs=0.2)
    ambiente.set_flag("chuva", False, "matheus")
    assert ambiente.lama_generalizada() is False
    assert ambiente.arestas_em_lama() == set()
    assert rota_leve.dijkstra_min("WC-01")["WC-02"] == pytest.approx(
        d / rota_leve.VELOCIDADE_M_MIN, abs=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# S04 — calor >30 °C sobe a procura
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s04():
    """Calor 33 °C ⇒ procura ×1.15; com chuva ×1.38; ≤30 °C não conta."""
    assert ambiente.procura_factor() == 1.0
    ambiente.set_flag("calor", True, "ricardo", temp_c=33.0)
    assert ambiente.procura_factor() == pytest.approx(1.15)
    assert ambiente.dwell_factor() == 1.0          # calor não mexe no dwell
    ambiente.set_flag("chuva", True, "ricardo")
    assert ambiente.procura_factor() == pytest.approx(1.38)
    ambiente.set_flag("chuva", False, "ricardo")
    ambiente.set_flag("calor", True, "ricardo", temp_c=28.0)
    assert ambiente.procura_factor() == 1.0
    assert ambiente.estado_resumo()["temp_c"] == 28.0


# ─────────────────────────────────────────────────────────────────────────────
# S05 — evacuação em bloco
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cenario_s05(client):
    """Evacuar wc-01+wc-06 em bloco: fechados, auditados, fora do route."""
    from app.services import decision_log
    demo.demo_tick(T0)
    r = await client.post("/api/v1/ambiente/evacuacao", json={
        "clusters": ["wc-01", "wc-06"], "utilizador": "ricardo",
        "justificacao": "drill de evacuação norte",
    })
    assert r.status_code == 200, r.text
    assert secoes_mf.is_fechado("wc-01") and secoes_mf.is_fechado("wc-06")
    regs = decision_log.query(tipo="evacuacao")
    assert len(regs) == 1 and regs[0]["utilizador"] == "ricardo"
    r = await client.get("/api/v1/route?origem=ENTRADA&genero=f")
    assert r.status_code == 200
    for o in r.json()["opcoes"]:
        assert o["wc"].split("_")[0] not in ("wc-01", "wc-06")


# ─────────────────────────────────────────────────────────────────────────────
# S06 — fechar cada um dos 8 clusters exclui-o do route
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("cid", ALL_CLUSTERS)
@pytest.mark.asyncio
async def test_cenario_s06(client, cid):
    """Cluster fechado sai das secções permitidas E do route no mesmo tick."""
    demo.demo_tick(T0)
    genero = "f"
    secoes_mf.set_fechado(cid, True, "goncalo", "drill por cluster")
    rota_leve.reset()
    permitidas = secoes_mf.seccoes_permitidas(genero)
    assert all(s.split("_")[0] != cid for s in permitidas)
    r = await client.get(f"/api/v1/route?origem=ENTRADA&genero={genero}")
    assert r.status_code == 200
    opcoes = r.json()["opcoes"]
    assert opcoes, "route sem opções com apenas 1 cluster fechado"
    assert all(o["wc"].split("_")[0] != cid for o in opcoes)


# ─────────────────────────────────────────────────────────────────────────────
# S07 — limpeza por SECÇÃO: WC-04_F não afecta WC-04_M
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s07():
    """WC-04_F em limpeza: serviço 0 e fora do route; a irmã M continua viva."""
    demo.demo_tick(T0)
    secoes_mf.set_limpeza("wc-04_f", True, 12, "matheus", "turno de limpeza")
    rota_leve.reset()
    assert secoes_mf.is_em_limpeza("wc-04_f") is True
    assert secoes_mf.is_em_limpeza("wc-04_m") is False
    assert secoes_mf.servico_pmin("wc-04_f") == 0.0
    assert secoes_mf.servico_pmin("wc-04_m") > 0.0
    assert "wc-04_f" not in secoes_mf.seccoes_permitidas("f")
    assert "wc-04_m" in secoes_mf.seccoes_permitidas("m")
    assert secoes_mf.alerta_fila("wc-04_f", 0.0) == "CRIT"
    r = rota_leve.compute_route("WC-04", "f", now_s=T0)
    assert all(o["wc"] != "wc-04_f" for o in r["opcoes"])


# ─────────────────────────────────────────────────────────────────────────────
# S08 — regra steward WC-05 + fecho exclui do route
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s08():
    """Bloqueio steward usa (interior+fila), NUNCA só interior; fechado sai."""
    # cap=133, espera=106.4 → limite = 0.85×239.4 = 203.49
    assert secoes_mf.wc05_bloquear_steward(133.0, 0.0) is False
    assert secoes_mf.wc05_bloquear_steward(130.0, 80.0) is True
    assert secoes_mf.wc05_bloquear_steward(100.0, 100.0) is False
    demo.demo_tick(T0)
    secoes_mf.set_fechado("wc-05", True, "steward", "bloqueio steward")
    rota_leve.reset()
    r = rota_leve.compute_route("ENTRADA", "f", now_s=T0)
    assert all(o["wc"] != "wc-05" for o in r["opcoes"])
    assert "wc-05" not in secoes_mf.seccoes_permitidas("f")


# ─────────────────────────────────────────────────────────────────────────────
# S09 — corte de ENTRADA|WC-05 dá alternativa
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s09():
    """Aresta cortada sai do grafo: WC-05 alcançável por ENTRADA→WC-03→WC-05."""
    demo.demo_tick(T0)
    base = rota_leve.dijkstra_min("ENTRADA")["WC-05"]
    ambiente.set_aresta_estado("ENTRADA|WC-05", "cortada", "matheus",
                               "vedação caída")
    rota_leve.reset()
    walk = rota_leve.dijkstra_min("ENTRADA")
    alt = (rota_leve._dist("ENTRADA", "WC-03")
           + distance_m("WC-03", "WC-05")) / rota_leve.VELOCIDADE_M_MIN
    assert walk["WC-05"] > base
    assert walk["WC-05"] == pytest.approx(alt, abs=0.1)
    r = rota_leve.compute_route("ENTRADA", "f", now_s=T0)
    assert r["recomendado"] is not None
    # reversível
    ambiente.set_aresta_estado("ENTRADA|WC-05", "normal", "matheus")
    assert rota_leve.dijkstra_min("ENTRADA")["WC-05"] == pytest.approx(
        base, abs=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# S10 — blackout: 10 min sem fontes
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cenario_s10(client):
    """Sem POSTs durante 10 min: decaimento, confiança baixa, zero NaN,
    /state continua 200."""
    for pos in ("porta", "meio", "fundo"):
        fr.ingest_wifi_bandas("wc-01", "m", pos, 30, 5, ts_ms=T0_MS, now_s=T0)
    fr.ingest_cabecas("wc-01", "m", 50, fonte="prosegur",
                      ts_ms=T0_MS + 1000, now_s=T0 + 1.0)
    p0 = fr.get_section_payload("wc-01_m", now_s=T0 + 1.0)
    assert p0["ocupacao"] == pytest.approx(50.0, abs=0.5)
    conf0 = p0["confianca_cruzada"]

    # 10 min de silêncio total: nós fora do TTL (3 min) → fonte offline
    p1 = fr.get_section_payload("wc-01_m", now_s=T0 + 601.0)
    assert p1["nos_online"] == 0
    assert p1["fonte_wifi"] == "offline"
    assert p1["ocupacao"] < p0["ocupacao"]          # decaimento (tau 20 min)
    assert p1["ocupacao"] == pytest.approx(
        50.0 * math.exp(-600.0 / fr.DECAY_TAU_S), abs=1.5)
    assert p1["confianca_cruzada"] < conf0          # confiança baixa
    assert _sem_nan(p1)
    assert _sem_nan(fr.get_all(now_s=T0 + 601.0))   # nenhum payload com NaN
    r = await client.get("/api/v1/state")
    assert r.status_code == 200
    assert _sem_nan(r.json())


# ─────────────────────────────────────────────────────────────────────────────
# S11 — gateway calado 3 min → offline + alerta
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s11():
    """Heartbeat → online; calado 3 min → offline + alerta_crit (uma vez)."""
    from app.services import decision_log
    gateways_hb.heartbeat("ug65-primario", now_s=T0)
    est = gateways_hb.estado(now_s=T0 + 10.0)
    assert est["ug65-primario"]["online"] is True
    assert est["lg308n-reserva"]["online"] is False
    est2 = gateways_hb.estado(now_s=T0 + 180.0)     # calado 3 min (>120 s)
    assert est2["ug65-primario"]["online"] is False
    regs = decision_log.query(tipo="alerta_crit", seccao="ug65-primario")
    assert len(regs) == 1
    assert "reserva assume" in regs[0]["justificacao"]
    gateways_hb.estado(now_s=T0 + 240.0)            # já offline: não duplica
    assert len(decision_log.query(tipo="alerta_crit",
                                  seccao="ug65-primario")) == 1


# ─────────────────────────────────────────────────────────────────────────────
# S12 — remover 1 e 2 nós mantém a estimativa coerente (mediana)
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s12():
    """3→2→1 nós: a mediana segura a agregação, sem saltos nem NaN."""
    est = fr.get_estimador("wc-03_m")
    for pos, macs in (("porta", 10), ("meio", 12), ("fundo", 14)):
        fr.ingest_wifi_bandas("wc-03", "m", pos, macs, 0, ts_ms=T0_MS, now_s=T0)
    fr.ingest_cabecas("wc-03", "m", 24, fonte="prosegur",
                      ts_ms=T0_MS + 1000, now_s=T0 + 1.0)
    assert est.wifi_zona(T0 + 1.0, "macs_A") == 12.0   # mediana(10,12,14)
    occ_3nos = est.ocupacao

    # remove 1 nó: só porta+meio voltam a postar → mediana(10,12)=11
    t1 = T0 + 240.0
    fr.ingest_wifi_bandas("wc-03", "m", "porta", 10, 0,
                          ts_ms=int(t1 * 1000), now_s=t1)
    fr.ingest_wifi_bandas("wc-03", "m", "meio", 12, 0,
                          ts_ms=int(t1 * 1000), now_s=t1)
    assert len(est._nos_online(t1)) == 2
    assert est.wifi_zona(t1, "macs_A") == 11.0
    p2 = fr.get_section_payload("wc-03_m", now_s=t1)
    assert abs(p2["ocupacao"] - occ_3nos) <= est.n_acessos * 40.0 * 5.0
    assert _sem_nan(p2)

    # remove 2 nós: só porta continua → mediana de 1 valor
    t2 = T0 + 480.0
    fr.ingest_wifi_bandas("wc-03", "m", "porta", 10, 0,
                          ts_ms=int(t2 * 1000), now_s=t2)
    assert len(est._nos_online(t2)) == 1
    assert est.wifi_zona(t2, "macs_A") == 10.0
    p1 = fr.get_section_payload("wc-03_m", now_s=t2)
    assert 0.0 <= p1["ocupacao"] <= p1["capacidade"]
    assert _sem_nan(p1)
    assert p1["confianca_cruzada"] < p2["confianca_cruzada"]   # menos nós


# ─────────────────────────────────────────────────────────────────────────────
# S13 — buffer local quando a persistência falha
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cenario_s13():
    """Postgres em baixo: snapshot vai para _PENDENTES e modo_degradado é
    registado UMA única vez (só na transição)."""
    from app.services import decision_log
    fr.ingest_cabecas("wc-01", "m", 20, fonte="prosegur",
                      ts_ms=T0_MS, now_s=T0)
    assert len(fr._PENDENTES) == 0 and fr._PG_EM_FALHA is False

    # session_factory=None → excepção dentro do try → buffer local
    await fr._persist_snapshot(None)
    assert len(fr._PENDENTES) == 1
    assert "wc-01_m" in fr._PENDENTES[0]["snap"]
    assert fr._PG_EM_FALHA is True
    regs = decision_log.query(tipo="modo_degradado")
    assert len(regs) == 1

    # segunda falha: acumula no buffer mas NÃO duplica o log
    await fr._persist_snapshot(None)
    assert len(fr._PENDENTES) == 2
    assert len(decision_log.query(tipo="modo_degradado")) == 1


# ─────────────────────────────────────────────────────────────────────────────
# S14 — fallback narrativo determinista (PT+EN, sem IA, <2.5 s)
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s14(monkeypatch):
    """_narrativa responde em PT-PT + EN em muito menos de 2.5 s sem chave IA."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    demo.demo_tick(T0)
    r = rota_leve.compute_route("ENTRADA", "f", now_s=T0)
    inicio = time.perf_counter()
    out = rota_leve._narrativa(r["opcoes"], None)
    duracao = time.perf_counter() - inicio
    assert duracao < 2.5
    assert out["pt"] and out["en"]
    assert "Recomendamos" in out["pt"]
    # mesmo sem opções nunca devolve ecrã vazio
    vazio = rota_leve._narrativa([], None)
    assert vazio["pt"] and vazio["en"]


# ─────────────────────────────────────────────────────────────────────────────
# S15 — warm start: payload pré == payload pós (to_dict/restore)
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s15():
    """Restart simulado: a_actual, âncora, fila e pares sobrevivem intactos."""
    for i in range(12):
        fr.ingest_wifi_bandas("wc-02", "f", "porta", 10 + i * 6, 14,
                              ts_ms=T0_MS + i * 60_000, now_s=T0 + i * 60.0)
        fr.ingest_cabecas("wc-02", "f", 8 + i * 3,
                          ts_ms=T0_MS + i * 60_000 + 1000,
                          now_s=T0 + i * 60.0 + 1.0)
    est = fr.get_estimador("wc-02_f")
    pre = est.payload(T0 + 12 * 60.0)
    pares_pre = est.regression_pairs()

    snapshot = {sid: e.to_dict() for sid, e in fr._ESTIMADORES.items()}
    fr.reset()
    for sid, estado in snapshot.items():
        fr.get_estimador(sid).restore(estado)

    est2 = fr.get_estimador("wc-02_f")
    pos = est2.payload(T0 + 12 * 60.0)
    assert pos == pre                                # payload pre == pos
    assert est2.regression_pairs() == pares_pre


# ─────────────────────────────────────────────────────────────────────────────
# S16 — surto pós-headliner ×3.8 + pré-surto penaliza
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s16():
    """_surge_factor=3.8 na janela de 25 min após um show REAL de state._SHOWS;
    pré-surto (T-10 min) penaliza clusters perto do palco."""
    from app.services.state import _SHOWS
    show = next(s for s in _SHOWS if s.headliner)
    end_s = datetime.fromisoformat(show.end_iso).timestamp()
    assert fr._surge_factor(end_s + 60.0) == fr.SURTO_FACTOR     # 3.8 na janela
    assert fr._surge_factor(end_s + 24 * 60.0) == fr.SURTO_FACTOR
    assert fr._surge_factor(end_s + 26 * 60.0) == 1.0            # fora
    assert fr._surge_factor(end_s - 60.0) == 1.0                 # antes do fim

    # pré-surto: T-5 min do fim do headliner devolve o palco e penaliza
    assert rota_leve._pre_surto(end_s - 300.0) == show.stage
    assert rota_leve._pre_surto(end_s - 20 * 60.0) is None
    penal = rota_leve._penal_surto("WC-06", show.stage)          # colado ao palco
    assert penal > 0.0
    r = rota_leve.compute_route("ENTRADA", "f", now_s=end_s - 300.0)
    assert r["pre_surto"] == show.stage
    o6 = next((o for o in r["opcoes"] if o["wc"] == "wc-06"), None)
    if o6 is not None:
        assert o6["surto"] == pytest.approx(penal, abs=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# S17 — dois shows sobrepostos não duplicam log nem rebentam
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s17(monkeypatch):
    """Dois shows sintéticos a acabar quase juntos: o motor responde, o surto
    activa UMA vez e a transição de modo_saida é registada UMA vez."""
    from app.services import decision_log
    demo.demo_tick(T0)
    shows = [_show(-60.0, show_id="s1"),
             _show(-120.0, stage="Super Bock Stage", show_id="s2")]
    monkeypatch.setattr("app.services.state.get_shows", lambda: shows)

    assert fr._surge_factor(T0) == fr.SURTO_FACTOR   # janela dos dois → 3.8 (1×)
    rota_leve.reset()
    r1 = rota_leve.compute_route("ENTRADA", "f", now_s=T0)
    r2 = rota_leve.compute_route("ENTRADA", "f", now_s=T0 + 30.0)
    assert r1["recomendado"] is not None and r2["recomendado"] is not None
    assert _sem_nan(r1) and _sem_nan(r2)
    assert r1["modo_saida"] is True and r2["modo_saida"] is True
    # transição False→True registada UMA vez, não uma por show nem por tick
    regs = decision_log.query(tipo="modo_saida")
    assert len(regs) == 1
    assert regs[0]["depois"]["activo"] is True


# ─────────────────────────────────────────────────────────────────────────────
# S18 — rampa de entrada NÃO dispara flag_anomalia
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s18():
    """Ocupação a subir devagar (rampa de abertura de portas): dentro da
    trava física → nunca flag_anomalia."""
    fr.ingest_wifi_bandas("wc-01", "m", "porta", 10, 0, ts_ms=T0_MS, now_s=T0)
    fr.ingest_cabecas("wc-01", "m", 10, fonte="prosegur",
                      ts_ms=T0_MS + 1000, now_s=T0 + 1.0)
    est = fr.get_estimador("wc-01_m")
    for i in range(1, 16):                       # +5 macs/min durante 15 min
        t = T0 + 60.0 * i
        p = fr.ingest_wifi_bandas("wc-01", "m", "porta", 10 + i * 5, 0,
                                  ts_ms=int(t * 1000), now_s=t)
        assert p["flag_anomalia"] is False, f"rampa marcou anomalia no min {i}"
    assert est.ocupacao > 10.0                   # a rampa subiu de facto
    assert not any(pt["anomalia"] for pt in est.history(20))


# ─────────────────────────────────────────────────────────────────────────────
# S19 — modo saída muda o payload do route
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s19(monkeypatch):
    """Último show terminado há 30 min: modo_saida=True e bónus −1.5 min nos
    clusters a <150 m da ENTRADA."""
    demo.demo_tick(T0)
    base = rota_leve.compute_route("ENTRADA", "f", now_s=T0)
    assert base["modo_saida"] is False
    base_por_wc = {o["wc"]: o["total_min"] for o in base["opcoes"]}

    monkeypatch.setattr("app.services.state.get_shows",
                        lambda: [_show(-30 * 60.0)])
    rota_leve.reset()
    r = rota_leve.compute_route("ENTRADA", "f", now_s=T0)
    assert r["modo_saida"] is True               # o payload mudou
    comparados = 0
    for o in r["opcoes"]:
        cid = o["wc"].split("_")[0].upper()
        if o["wc"] in base_por_wc and rota_leve._dist(cid, "ENTRADA") < 150.0:
            esperado = round(max(0.1, base_por_wc[o["wc"]] - 1.5), 1)
            assert o["total_min"] == pytest.approx(esperado, abs=0.11)
            comparados += 1
    assert comparados >= 1


# ─────────────────────────────────────────────────────────────────────────────
# S20 — flag_congestao: multidão parada ≠ fila a fluir
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s20():
    """Ocupação >75% PARADA (≥5 pontos sem variação) dispara; a fluir não."""
    from app.services import decision_log
    # parado: 60/72 constante durante 6 min
    for i in range(6):
        fr.ingest_cabecas("wc-01", "m", 60, fonte="prosegur",
                          ts_ms=T0_MS + i * 60_000, now_s=T0 + i * 60.0)
    p = fr.get_section_payload("wc-01_m", now_s=T0 + 6 * 60.0)
    assert p["flag_congestao"] is True
    assert len(decision_log.query(tipo="congestao", seccao="wc-01_m")) == 1

    # a fluir: mesma ocupação média mas a variar (60↔66, cap_f WC-02 = 72)
    for i in range(6):
        fr.ingest_cabecas("wc-02", "f", 60 if i % 2 == 0 else 66,
                          fonte="prosegur", ts_ms=T0_MS + i * 60_000,
                          now_s=T0 + i * 60.0)
    p2 = fr.get_section_payload("wc-02_f", now_s=T0 + 6 * 60.0)
    assert p2["ocupacao"] / p2["capacidade"] > 0.75   # cheio…
    assert p2["flag_congestao"] is False              # …mas a fluir


# ─────────────────────────────────────────────────────────────────────────────
# S21 — saturação sintética → recusas_estimadas > 0
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cenario_s21(client):
    """Fila acima da queue_cap ⇒ recusas >0, expostas em /sections/estado."""
    # recusas_estimadas lê em tempo real → a saturação é criada no "agora"
    agora = time.time()
    # macs_B enorme → fila clamp a queue_cap×1.5 > queue_cap → excesso >0
    fr.ingest_cabecas("wc-01", "f", 20, fonte="prosegur",
                      ts_ms=int(agora * 1000), now_s=agora)
    fr.ingest_wifi_bandas("wc-01", "f", "porta", 40, 1000,
                          ts_ms=int(agora * 1000) + 1000, now_s=agora + 1.0)
    p = fr.get_section_payload("wc-01_f", now_s=agora + 1.0)
    qc = secoes_mf.queue_cap("wc-01_f")
    assert p["fila_estimada"] > qc
    recusas = secoes_mf.recusas_estimadas()
    assert recusas["f"] > 0.0
    assert recusas["total"] > 0.0
    r = await client.get("/api/v1/sections/estado")
    assert r.status_code == 200
    assert r.json()["recusas_estimadas"]["total"] > 0.0


# ─────────────────────────────────────────────────────────────────────────────
# S22 — tempestade perfeita
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_cenario_s22(client, monkeypatch):
    """Chuva + WC-06 fechado + aresta cortada DURANTE o surto pós-show:
    /route 200, payload sem NaN, o cluster fechado NUNCA nas opções."""
    demo.demo_tick(T0)
    agora = time.time()
    # show a acabar há 60 s do "agora" real → surto activo também via API
    monkeypatch.setattr("app.services.state.get_shows",
                        lambda: [_show(-60.0, base_s=agora)])
    ambiente.set_flag("chuva", True, "ricardo", intensidade="forte",
                      justificacao="tempestade")
    secoes_mf.set_fechado("wc-06", True, "ricardo", "inundação")
    ambiente.set_aresta_estado("WC-01|WC-08", "cortada", "ricardo",
                               "vedação caída")
    rota_leve.reset()

    assert fr._surge_factor(agora) == fr.SURTO_FACTOR    # surto activo
    for genero in ("f", "m"):
        for origem in ("ENTRADA", "PALCO_MUNDO", "WC-08"):
            r = await client.get(f"/api/v1/route?origem={origem}"
                                 f"&genero={genero}")
            assert r.status_code == 200, r.text
            d = r.json()
            assert _sem_nan(d), f"NaN no route {origem}/{genero}"
            assert d["recomendado"] is not None
            assert all(o["wc"].split("_")[0] != "wc-06" for o in d["opcoes"]), \
                f"cluster fechado nas opções ({origem}/{genero})"


# ─────────────────────────────────────────────────────────────────────────────
# S23 — memória entre dias: o a aprendido em D1 vive em D3
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s23():
    """Snapshot de D1 restaurado num processo D3: os pares >3h expiram na
    próxima add_pair mas o a/b/r2 aprendidos FICAM."""
    # D1: treina a regressão (c = 2·w + 5 → a→2.0)
    for i in range(12):
        fr.ingest_wifi_bandas("wc-01", "m", "porta", 10 + i * 4, 0,
                              ts_ms=T0_MS + i * 60_000, now_s=T0 + i * 60.0)
        fr.ingest_cabecas("wc-01", "m", 2.0 * (10 + i * 4) + 5.0,
                          fonte="prosegur", ts_ms=T0_MS + i * 60_000 + 1000,
                          now_s=T0 + i * 60.0 + 1.0)
    est_d1 = fr.get_estimador("wc-01_m")
    assert est_d1.regressao.fitted
    a_d1 = est_d1.regressao.a
    assert a_d1 == pytest.approx(2.0, abs=0.05)        # aprendeu, não é a0
    snap_d1 = est_d1.to_dict()

    # "D3": processo novo, snapshot antigo (>24h) restaurado por inteiro
    fr.reset()
    est_d3 = fr.get_estimador("wc-01_m")
    est_d3.restore(snap_d1)
    assert est_d3.regressao.a == a_d1                  # a sobreviveu ao reload
    assert est_d3.regressao.fitted is True
    assert len(est_d3.regressao.pares) >= 10           # pares vieram no snapshot

    # primeira âncora de D3 (T0 + 2 dias): os pares de D1 expiram (>3h)…
    d3 = T0 + 2 * 86400.0
    fr.ingest_wifi_bandas("wc-01", "m", "porta", 30, 0,
                          ts_ms=int(d3 * 1000), now_s=d3)
    fr.ingest_cabecas("wc-01", "m", 65, fonte="prosegur",
                      ts_ms=int(d3 * 1000) + 1000, now_s=d3 + 1.0)
    assert len(est_d3.regressao.pares) == 1            # janela limpa-se sozinha
    # …mas o declive aprendido em D1 continua a comandar a estimativa
    assert est_d3.regressao.a == a_d1
    assert est_d3.payload(d3 + 1.0)["a_actual"] == round(a_d1, 3)


# ─────────────────────────────────────────────────────────────────────────────
# S24 — quarentena de nó (sensor a mentir)
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s24():
    """Nó persistentemente fora da mediana (|z|>3 por ≥10 min) entra em
    quarentena, sai da agregação e fica auditado; sair exige utilizador."""
    from app.services import decision_log
    for i in range(12):                          # 11 min de desvio a 60 s
        ts, agora = T0_MS + i * 60_000, T0 + i * 60.0
        fr.ingest_wifi_bandas("wc-01", "m", "porta", 10, 0, ts_ms=ts, now_s=agora)
        fr.ingest_wifi_bandas("wc-01", "m", "meio", 11, 0, ts_ms=ts, now_s=agora)
        fr.ingest_wifi_bandas("wc-01", "m", "fundo", 500, 0, ts_ms=ts, now_s=agora)
    est = fr.get_estimador("wc-01_m")
    assert "fundo" in est.quarentena
    assert est.wifi_zona(T0 + 11 * 60.0, "macs_A") == pytest.approx(10.5)
    p = fr.get_section_payload("wc-01_m", now_s=T0 + 11 * 60.0)
    assert p["nos_quarentena"] == ["fundo"]
    regs = decision_log.query(tipo="quarentena_no")
    assert len(regs) == 1 and regs[0]["origem"] == "motor"
    # remoção sem utilizador é PROIBIDA; com utilizador remove e audita
    with pytest.raises(ValueError):
        fr.remover_quarentena("wc-01_m", "fundo", "")
    out = fr.remover_quarentena("wc-01_m", "fundo", "matheus")
    assert out["removido"] is True
    assert len(decision_log.query(tipo="quarentena_removida")) == 1


# ─────────────────────────────────────────────────────────────────────────────
# S25 — ts_suspeito (relógio errado)
# ─────────────────────────────────────────────────────────────────────────────
def test_cenario_s25():
    """Nó/âncora com relógio >5 min desviado: aceite, marcado, NÃO funde;
    volta a fundir quando chega ts são."""
    for pos in ("porta", "meio"):
        fr.ingest_wifi_bandas("wc-07", "m", pos, 10, 0, ts_ms=T0_MS, now_s=T0)
    fr.ingest_cabecas("wc-07", "m", 20, fonte="prosegur",
                      ts_ms=T0_MS + 1000, now_s=T0 + 1.0)
    est = fr.get_estimador("wc-07_m")
    pares_antes = len(est.regressao.pares)
    occ_antes = est.ocupacao
    # nó com ts 10 min no futuro → marcado, fora da mediana
    p = fr.ingest_wifi_bandas("wc-07", "m", "fundo", 400, 0,
                              ts_ms=T0_MS + 600_000, now_s=T0 + 1.0)
    assert est.nos["fundo"]["ts_suspeito"] is True
    assert "fundo" in p["ts_suspeitos"]
    assert est.wifi_zona(T0 + 1.0, "macs_A") == pytest.approx(10.0)
    assert est.ocupacao == pytest.approx(occ_antes, abs=0.1)
    # âncora com ts errado → não cria par nem re-baseia
    p = fr.ingest_cabecas("wc-07", "m", 999, fonte="luxonis",
                          ts_ms=T0_MS + 600_000, now_s=T0 + 2.0)
    assert len(est.regressao.pares) == pares_antes
    assert est.c_ultima == 20.0
    assert "ancora" in p["ts_suspeitos"]
    # ts são repõe a fusão do nó
    fr.ingest_wifi_bandas("wc-07", "m", "fundo", 12, 0,
                          ts_ms=T0_MS + 120_000, now_s=T0 + 120.0)
    assert est.nos["fundo"]["ts_suspeito"] is False
    p = fr.get_section_payload("wc-07_m", now_s=T0 + 120.0)
    assert "fundo" not in p["ts_suspeitos"]

"""Tests for the Flow engine — NorthStar §3 compliance."""
from __future__ import annotations
import pytest


def _run_sim_90min():
    """90 min festival simulation. Returns (page_dict, engine)."""
    from app.services.flow import FlowEngine, SensorReading, CLUSTERS
    eng = FlowEngine()
    t0 = 1_750_000_000.0
    cum = {(cid, sec): {"in": 0, "out_real": 0, "out_ir": 0}
           for cid in CLUSTERS for sec in eng._secs(cid)}

    def arrivals(minute, cid, sec):
        base = {"wc-03": 7, "wc-05": 9, "wc-02": 8, "wc-07": 7,
                "wc-04": 7, "wc-01": 5, "wc-06": 4, "wc-08": 3}[cid]
        surge = 3.8 if 60 <= minute < 85 else 1.0
        if CLUSTERS[cid].dist_m > 200 and surge > 1:
            surge = 1.2
        return int(base * surge)

    for minute in range(85):
        ts = t0 + minute * 60
        for cid in CLUSTERS:
            ent, sai, cam = {}, {}, {}
            for sec in eng._secs(cid):
                cap = CLUSTERS[cid].cap[sec]
                mu = max(int(cap / 6), 4)
                occ_now = max(cum[(cid, sec)]["in"] - cum[(cid, sec)]["out_real"], 0)
                a = arrivals(minute, cid, sec)
                if occ_now > 0.95 * cap:
                    a = int(a * 0.4)
                d_out = min(mu, occ_now + a)
                cum[(cid, sec)]["in"] += a
                cum[(cid, sec)]["out_real"] += d_out
                real_occ = min(max(cum[(cid, sec)]["in"] - cum[(cid, sec)]["out_real"], 0), cap)
                cum[(cid, sec)]["out_ir"] += int(d_out * 0.94)
                ent[sec] = cum[(cid, sec)]["in"]
                sai[sec] = cum[(cid, sec)]["out_ir"]
                cam[sec] = real_occ
            contagem_cam = None if (cid == "wc-06" and minute >= 70) else cam
            wifi = sum(min(max(cum[(cid, s)]["in"] - cum[(cid, s)]["out_real"], 0),
                           CLUSTERS[cid].cap[s]) for s in eng._secs(cid))
            eng.ingest(SensorReading(
                cluster_id=cid, ts=ts,
                entradas_ir=ent, saidas_ir=sai,
                pessoas_wifi=int(wifi * 1.1),
                contagem_cam=contagem_cam, uptime_s=minute * 60,
            ))
        eng.tick_route(surge=3.8 if 60 <= minute < 85 else 1.0)
    return eng.flow_page(), eng


@pytest.fixture(scope="module")
def sim_result():
    return _run_sim_90min()


def test_flow_ocupacao_clampada_100(sim_result):
    page, _ = sim_result
    for s in page["secoes"]:
        assert 0 <= s["ocupacao_pct"] <= 100, f"ocupacao fora de [0,100]: {s}"


def test_flow_confianca_sempre_presente(sim_result):
    page, _ = sim_result
    for s in page["secoes"]:
        assert 5 <= s["confianca_pct"] <= 99, f"confianca fora de [5,99]: {s}"
        assert s["fontes_activas"], f"fontes_activas vazio: {s}"


def test_flow_queda_camara_renormaliza(sim_result):
    """wc-06 perdeu câmara: só IR+WiFi, sem crash."""
    page, _ = sim_result
    wc06 = next(s for s in page["secoes"] if s["cluster_id"] == "wc-06")
    assert "Camera" not in wc06["fontes_activas"], f"Camera nao devia estar activa: {wc06}"
    assert wc06["confianca_pct"] >= 5


def test_flow_routing_produziu_redirects(sim_result):
    page, _ = sim_result
    assert len(page["routing"]) > 0, "routing vazio durante surge"
    for r in page["routing"]:
        assert r["de"] != r["para"], f"redirect para o mesmo cluster: {r}"


def test_flow_kpis_no_intervalo(sim_result):
    page, _ = sim_result
    k = page["kpis"]
    assert 0 <= k["kpi_01"] <= 100
    assert 0 <= k["kpi_02"] <= 100
    assert k["kpi_04"] >= 0


def test_flow_congestionamento_detectado(sim_result):
    page, _ = sim_result
    congest = [s for s in page["secoes"] if s["congestionado"]]
    assert congest, "nenhum congestionamento detectado no surge"


def test_flow_reancora_repoe_deriva_a_zero(sim_result):
    _, eng = sim_result
    from app.services.flow import CLUSTERS
    cid, sec = "wc-03", "M"
    eng._state[(cid, sec)].deriva = 999.0
    eng.reanchor(cid, sec, 10.0)
    assert eng._state[(cid, sec)].deriva == 0.0
    assert eng._state[(cid, sec)].residual == 0.0


def test_flow_sem_divisao_por_zero():
    """Motor com zero fontes não crasha e devolve confiança mínima."""
    from app.services.flow import FlowEngine, SensorReading, CLUSTERS
    eng = FlowEngine()
    # Feed com zeros (sem IR, sem WiFi, sem câmara)
    for cid in CLUSTERS:
        eng.ingest(SensorReading(
            cluster_id=cid, ts=1_750_000_000.0,
            entradas_ir={s: 0 for s in eng._secs(cid)},
            saidas_ir={s: 0 for s in eng._secs(cid)},
            pessoas_wifi=None, contagem_cam=None, uptime_s=0,
        ))
    page = eng.flow_page()
    for s in page["secoes"]:
        assert 0 <= s["ocupacao_pct"] <= 100


def test_flow_selftest_passes():
    """Corre o auto-teste embutido do motor."""
    from app.services.flow import _selftest
    _selftest()  # raises AssertionError se algo falhar

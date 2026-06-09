"""
Testes da fusão rolante CABEÇAS + WIFI (app/services/fusao_rolante.py).

Cobre (mínimo exigido):
  - regressão converge com dados sintéticos lineares
  - guarda var<0.5 mantém o a anterior
  - clamp do a em [0.3, 4.0]
  - trava física trunca pico de 500 macs (+flag_anomalia)
  - decaimento exponencial sem nós online
  - confiança nunca NaN/inf, sempre em [0, 1]
  - clusters unissexo (WC-05/06) com UMA secção, sem campos M/F
  - 422 em payload inválido
  - fluxo API completo: cabeças + 3 WiFi → /api/v1/fusion coerente
"""
from __future__ import annotations

import math

import pytest

from app.services import fusao_rolante as fr
from app.services import node_calibration as nc
from app.services.fusao_rolante import (
    A_MAX, A_MIN, A0_EXTERIOR, A0_INTERIOR, RegressaoRolante,
)

# Base temporal sintética (fora de qualquer janela de surto pós-show)
T0 = 1_750_000_000.0          # epoch s
T0_MS = int(T0 * 1000)


@pytest.fixture(autouse=True)
def _estado_limpo():
    """Cada teste parte de fusão rolante e calibração virgens."""
    fr.reset()
    nc.reset()
    yield
    fr.reset()
    nc.reset()


# ─────────────────────────────────────────────────────────────────────────────
# Regressão rolante
# ─────────────────────────────────────────────────────────────────────────────
class TestRegressaoRolante:
    def test_converge_com_dados_lineares(self):
        """c = 2·w + 5 → a→2.0, b→5.0, R²→1.0."""
        r = RegressaoRolante(A0_EXTERIOR)
        for i, w in enumerate(range(0, 24, 2)):
            r.add_pair(w, 2.0 * w + 5.0, T0 + i * 60.0)
        assert r.fitted
        assert r.a == pytest.approx(2.0, abs=0.01)
        assert r.b == pytest.approx(5.0, abs=0.1)
        assert r.r2 == pytest.approx(1.0, abs=0.01)

    def test_guarda_var_baixa_mantem_a_anterior(self):
        """var(w) < 0.5 → fit recusado, a/b mantêm-se."""
        r = RegressaoRolante(A0_EXTERIOR)
        for i in range(10):
            r.add_pair(10.0, 5.0 + i, T0 + i * 60.0)   # w constante → var=0
        assert not r.fitted
        assert r.a == A0_EXTERIOR
        assert r.b == 0.0

    def test_guarda_var_mantem_fit_anterior(self):
        """Depois de um fit válido, dados sem variância não o destroem."""
        r = RegressaoRolante(A0_EXTERIOR)
        for i, w in enumerate(range(0, 20, 2)):
            r.add_pair(w, 1.5 * w, T0 + i * 60.0)
        assert r.fitted
        # janela cheia de pares constantes → var→0 → guarda activa
        for i in range(36):
            r.add_pair(7.0, 10.0, T0 + 4000.0 + i * 60.0)
        a_guardado = r.a
        # mais pares constantes: var=0 < 0.5 → a NÃO muda
        for i in range(10):
            r.add_pair(7.0, 10.0, T0 + 8000.0 + i * 60.0)
        assert r.a == a_guardado
        assert A_MIN <= r.a <= A_MAX

    def test_clamp_a_maximo(self):
        """Declive real 10 → a truncado a 4.0."""
        r = RegressaoRolante(A0_EXTERIOR)
        for i, w in enumerate(range(0, 12)):
            r.add_pair(w, 10.0 * w, T0 + i * 60.0)
        assert r.a == A_MAX

    def test_clamp_a_minimo(self):
        """Declive real 0.05 → a truncado a 0.3."""
        r = RegressaoRolante(A0_EXTERIOR)
        for i, w in enumerate(range(0, 12)):
            r.add_pair(w, 0.05 * w, T0 + i * 60.0)
        assert r.a == A_MIN

    def test_janela_3_horas_expira_pares(self):
        r = RegressaoRolante(A0_EXTERIOR)
        r.add_pair(1.0, 1.0, T0)
        r.add_pair(2.0, 2.0, T0 + 4 * 3600.0)   # 4h depois → o 1º par sai
        assert len(r.pares) == 1

    def test_janela_36_pares(self):
        r = RegressaoRolante(A0_EXTERIOR)
        for i in range(50):
            r.add_pair(float(i), float(i), T0 + i * 60.0)
        assert len(r.pares) == 36


# ─────────────────────────────────────────────────────────────────────────────
# Estimador por secção (âncora + tendência + trava + decaimento)
# ─────────────────────────────────────────────────────────────────────────────
class TestEstimadorSeccao:
    def test_ancora_define_ocupacao(self):
        p = fr.ingest_cabecas("wc-01", "m", 30, fonte="prosegur", ts_ms=T0_MS)
        assert p is not None
        assert p["ocupacao"] == 30.0
        assert p["idade_ancora_s"] == 0.0

    def test_trava_fisica_trunca_pico_500_macs(self):
        """Pico de 500 macs num minuto → truncado a n_acessos×40 + flag."""
        fr.ingest_wifi_bandas("wc-01", "m", "porta", 10, 0, ts_ms=T0_MS)
        fr.ingest_cabecas("wc-01", "m", 10, fonte="prosegur",
                          ts_ms=T0_MS + 60_000)
        p = fr.ingest_wifi_bandas("wc-01", "m", "porta", 500, 0,
                                  ts_ms=T0_MS + 120_000)
        est = fr.get_estimador("wc-01_m")
        # 1 acesso × 40 p/min × 1 min = delta máximo 40 sobre a âncora (10)
        assert est.n_acessos == 1
        assert p["ocupacao"] == pytest.approx(50.0, abs=0.1)
        assert p["flag_anomalia"] is True

    def test_ocupacao_clamp_capacidade(self):
        """Estimativa nunca excede a capacidade da secção (clusters_geo)."""
        fr.ingest_wifi_bandas("wc-01", "f", "porta", 20, 0, ts_ms=T0_MS)
        fr.ingest_cabecas("wc-01", "f", 60, ts_ms=T0_MS + 60_000)
        ts = T0_MS + 120_000
        p = None
        for i in range(30):   # subida contínua → satura na capacidade
            p = fr.ingest_wifi_bandas("wc-01", "f", "porta", 20 + (i + 1) * 80,
                                      0, ts_ms=ts + i * 60_000)
        est = fr.get_estimador("wc-01_f")
        assert est.capacidade == 63          # cap_f de WC-01 em clusters_geo
        assert p["ocupacao"] <= 63.0

    def test_decaimento_sem_nos(self):
        """0 nós online → decaimento exponencial com tau de 20 min."""
        fr.ingest_wifi_bandas("wc-02", "m", "porta", 30, 0, ts_ms=T0_MS)
        fr.ingest_cabecas("wc-02", "m", 50, ts_ms=T0_MS + 1000)
        # 20 min depois, nó stale (TTL 3 min) → occ ≈ 50/e
        p = fr.get_section_payload("wc-02_m", now_s=T0 + 1.0 + 20 * 60.0)
        assert p["nos_online"] == 0
        assert p["fonte_wifi"] == "offline"
        assert p["ocupacao"] == pytest.approx(50.0 / math.e, abs=1.0)

    def test_mediana_entre_nos_nao_media(self):
        """Agregação por mediana: outlier num nó não arrasta a secção."""
        est = fr.get_estimador("wc-03_m")
        fr.ingest_wifi_bandas("wc-03", "m", "porta", 10, 0, ts_ms=T0_MS)
        fr.ingest_wifi_bandas("wc-03", "m", "meio", 12, 0, ts_ms=T0_MS)
        fr.ingest_wifi_bandas("wc-03", "m", "fundo", 500, 0, ts_ms=T0_MS)
        w = est.wifi_zona(T0, "macs_A")
        assert w == 12.0     # mediana(10, 12, 500) — a média seria 174

    def test_no_stale_sai_do_calculo(self):
        est = fr.get_estimador("wc-04_m")
        fr.ingest_wifi_bandas("wc-04", "m", "porta", 10, 0, ts_ms=T0_MS)
        fr.ingest_wifi_bandas("wc-04", "m", "meio", 40, 0,
                              ts_ms=T0_MS + 240_000)   # 4 min depois
        # "porta" não posta há 4 min → fora do TTL de 3 min
        assert est.wifi_zona(T0 + 240.0, "macs_A") == 40.0
        assert len(est._nos_online(T0 + 240.0)) == 1

    def test_fila_estimada_zona_b(self):
        """fila = a × mediana(macs_zona_B/k), com clamp à capacidade."""
        p = fr.ingest_wifi_bandas("wc-01", "m", "porta", 10, 20, ts_ms=T0_MS)
        est = fr.get_estimador("wc-01_m")
        assert p["fila_estimada"] == pytest.approx(est.regressao.a * 20.0, abs=0.1)

    def test_a0_interior_e_exterior(self):
        """a0 = 0.45 exterior · 0.55 interior fechado (WC-05/06)."""
        assert fr.get_estimador("wc-01_m").regressao.a == A0_EXTERIOR
        assert fr.get_estimador("wc-05").regressao.a == A0_INTERIOR
        assert fr.get_estimador("wc-06").regressao.a == A0_INTERIOR

    def test_calibracao_k_divide_contagem(self):
        """k=2.0 num nó → a sua contagem é dividida por 2 na agregação."""
        node_id = "wc-07_m_porta"
        assert nc.update_node(node_id, k=2.0) is not None
        est = fr.get_estimador("wc-07_m")
        fr.ingest_wifi_bandas("wc-07", "m", node_id, 40, 0, ts_ms=T0_MS)
        assert est.wifi_zona(T0, "macs_A") == 20.0


# ─────────────────────────────────────────────────────────────────────────────
# Confiança cruzada — nunca NaN/inf
# ─────────────────────────────────────────────────────────────────────────────
class TestConfiancaCruzada:
    def test_nunca_nan_inf_em_nenhum_estado(self):
        est = fr.get_estimador("wc-08_m")
        # estado virgem (sem cabeças, sem fit, 0 nós)
        for now in (T0, T0 + 1e9, 0.0):
            c = est.confianca_cruzada(now)
            assert math.isfinite(c) and 0.0 <= c <= 1.0
        # só wifi
        fr.ingest_wifi_bandas("wc-08", "m", "porta", 10, 0, ts_ms=T0_MS)
        c = est.confianca_cruzada(T0)
        assert math.isfinite(c) and 0.0 <= c <= 1.0
        # wifi + âncora
        fr.ingest_cabecas("wc-08", "m", 12, ts_ms=T0_MS + 1000)
        c = est.confianca_cruzada(T0 + 1.0)
        assert math.isfinite(c) and 0.0 < c <= 1.0
        # âncora muito antiga (c1 → 0)
        c = est.confianca_cruzada(T0 + 1e7)
        assert math.isfinite(c) and 0.0 <= c <= 1.0

    def test_ancora_fresca_e_nos_todos_online_da_confianca_alta(self):
        for pos in ("porta", "meio", "fundo"):
            fr.ingest_wifi_bandas("wc-01", "m", pos, 10, 0, ts_ms=T0_MS)
        fr.ingest_cabecas("wc-01", "m", 12, fonte="prosegur",
                          ts_ms=T0_MS + 1000)
        p = fr.get_section_payload("wc-01_m", now_s=T0 + 1.0)
        assert p["nos_online"] == 3
        assert 0.9 < p["confianca_cruzada"] <= 1.0

    def test_um_no_reduz_confianca(self):
        """1 nó online em 3 → c3 baixa → confiança reduzida vs 3 nós."""
        fr.ingest_wifi_bandas("wc-01", "m", "porta", 10, 0, ts_ms=T0_MS)
        c_1no = fr.get_estimador("wc-01_m").confianca_cruzada(T0)
        for pos in ("porta", "meio", "fundo"):
            fr.ingest_wifi_bandas("wc-02", "m", pos, 10, 0, ts_ms=T0_MS)
        c_3nos = fr.get_estimador("wc-02_m").confianca_cruzada(T0)
        assert c_1no < c_3nos


# ─────────────────────────────────────────────────────────────────────────────
# API — ingestão, exposição e validação
# ─────────────────────────────────────────────────────────────────────────────
class TestAPIFusaoRolante:
    @pytest.mark.asyncio
    async def test_fluxo_cabecas_mais_wifi_fusion_coerente(self, client):
        """POST cabeças + 3 POSTs wifi → /api/v1/fusion com ocupação coerente
        e confianca_cruzada em (0,1]."""
        # ts omitido → tempo real (o GET também lê em tempo real)
        for i, pos in enumerate(("porta", "meio", "fundo")):
            r = await client.post("/api/v1/ingest", json={
                "cluster": "wc-01", "secao": "m", "no": pos,
                "macs_A": 40 + i * 4, "macs_B": 8,
            })
            assert r.status_code == 200, r.text
            assert r.json()["ok"] is True
        r = await client.post("/api/v1/ingest", json={
            "cluster": "wc-01", "secao": "m", "cabecas": 30,
            "fonte": "prosegur",
        })
        assert r.status_code == 200, r.text
        assert r.json()["tipo"] == "cabecas"

        r = await client.get("/api/v1/fusion")
        assert r.status_code == 200
        sec = r.json()["clusters"]["wc-01"]["seccoes"]["m"]
        assert 0.0 <= sec["ocupacao"] <= 72.0       # cap_m WC-01 (clusters_geo)
        assert sec["ocupacao"] == pytest.approx(30.0, abs=1.0)  # âncora fresca
        assert 0.0 < sec["confianca_cruzada"] <= 1.0
        assert sec["a_actual"] == pytest.approx(A0_EXTERIOR, abs=0.001)
        assert sec["nos_online"] == 3
        assert sec["idade_ancora_s"] is not None
        assert sec["flag_anomalia"] is False

    @pytest.mark.asyncio
    async def test_state_inclui_campos_rolantes(self, client):
        for pos in ("porta", "meio", "fundo"):
            await client.post("/api/v1/ingest", json={
                "cluster": "wc-01", "secao": "f", "no": pos,
                "macs_A": 20, "macs_B": 5,
            })
        await client.post("/api/v1/ingest", json={
            "cluster": "wc-01", "secao": "f", "cabecas": 25, "fonte": "luxonis",
        })
        r = await client.get("/api/v1/state")
        assert r.status_code == 200
        sec = next(s for s in r.json()["sections"]
                   if s["section_id"] == "WC-01_F")
        assert sec["confianca_cruzada"] is not None
        assert 0.0 < sec["confianca_cruzada"] <= 1.0
        assert sec["a_actual"] == pytest.approx(A0_EXTERIOR, abs=0.001)
        assert sec["nos_online"] == 3
        assert sec["flag_anomalia"] is False
        assert sec["fila_estimada"] is not None
        assert 0.0 <= sec["ocupacao_pct"] <= 100.0

    @pytest.mark.asyncio
    async def test_unissexo_uma_seccao_sem_mf(self, client):
        """WC-05/WC-06: UMA secção ('u'), nunca split M/F."""
        for cid in ("wc-05", "wc-06"):
            r = await client.post("/api/v1/ingest", json={
                "cluster": cid, "no": "porta", "macs_A": 50, "macs_B": 10,
            })
            assert r.status_code == 200, r.text
            r = await client.post("/api/v1/ingest", json={
                "cluster": cid, "cabecas": 40, "fonte": "prosegur",
            })
            assert r.status_code == 200, r.text

        r = await client.get("/api/v1/fusion")
        clusters = r.json()["clusters"]
        for cid in ("wc-05", "wc-06"):
            seccoes = clusters[cid]["seccoes"]
            assert set(seccoes.keys()) == {"u"}     # sem campos m/f
            assert seccoes["u"]["secao"] == "u"
        # secao enviada por engano num unissexo é ignorada (nunca cria split)
        r = await client.post("/api/v1/ingest", json={
            "cluster": "wc-05", "secao": "m", "no": "fundo",
            "macs_A": 10, "macs_B": 0,
        })
        assert r.status_code == 200
        assert r.json()["secao"] == "u"

    @pytest.mark.asyncio
    async def test_422_payloads_invalidos(self, client):
        casos = [
            {},                                                       # vazio
            {"cluster": "wc-01"},                                     # incompleto
            {"cluster": "wc-01", "secao": "m", "no": "porta",
             "macs_A": -5, "macs_B": 0},                              # negativo
            {"cluster": "wc-01", "secao": "m", "cabecas": -1},        # negativo
            {"cluster": "wc-99", "secao": "m", "no": "porta",
             "macs_A": 1, "macs_B": 0},                               # cluster ?
            {"cluster": "wc-01", "no": "porta",
             "macs_A": 1, "macs_B": 0},                               # MF sem secao
            {"cluster": "wc-01", "secao": "x", "cabecas": 5},         # secao ?
            {"cluster": "wc-01", "secao": "m", "no": "porta",
             "macs_A": "muitos", "macs_B": 0},                        # tipo errado
        ]
        for body in casos:
            r = await client.post("/api/v1/ingest", json=body)
            assert r.status_code == 422, f"{body} → {r.status_code}: {r.text}"
            assert "application/json" in r.headers["content-type"]

    @pytest.mark.asyncio
    async def test_ingest_legado_continua_a_funcionar(self, client):
        """O formato canónico {cluster_id, params} não foi quebrado."""
        r = await client.post("/api/v1/ingest", json={
            "cluster_id": "wc-03",
            "params": {"telemoveis_detectados": 34, "pessoas_estimadas": 25,
                       "estado_sensor": "okay"},
        })
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        assert r.json()["cluster_id"] == "wc-03"

    @pytest.mark.asyncio
    async def test_calibration_get_e_put(self, client):
        r = await client.get("/api/v1/calibration")
        assert r.status_code == 200
        data = r.json()
        # 6 clusters MF × 2 secções × 3 nós + 2 unissexo × 2 nós = 40
        assert data["total"] == 40
        assert all(n["k"] == 1.0 for n in data["nodes"])

        r = await client.put("/api/v1/calibration/wc-01_m_porta",
                             json={"k": 1.8, "threshold_dbm": -55.0})
        assert r.status_code == 200
        assert r.json()["node"]["k"] == 1.8

        r = await client.get("/api/v1/calibration/wc-01_m_porta")
        assert r.json()["k"] == 1.8

        # nó desconhecido → 404 JSON; k inválido → 422
        r = await client.put("/api/v1/calibration/no-fantasma", json={"k": 2.0})
        assert r.status_code == 404
        r = await client.put("/api/v1/calibration/wc-01_m_porta",
                             json={"k": -1.0})
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Snapshot — serialização round-trip
# ─────────────────────────────────────────────────────────────────────────────
class TestSnapshot:
    def test_to_dict_restore_roundtrip(self):
        fr.ingest_wifi_bandas("wc-01", "m", "porta", 10, 2, ts_ms=T0_MS)
        fr.ingest_cabecas("wc-01", "m", 15, fonte="prosegur",
                          ts_ms=T0_MS + 1000)
        est = fr.get_estimador("wc-01_m")
        estado = est.to_dict()

        fr.reset()
        est2 = fr.get_estimador("wc-01_m")
        est2.restore(estado)
        assert est2.c_ultima == 15.0
        assert est2.tem_dados is True
        assert est2.ocupacao == pytest.approx(est.ocupacao or 15.0, abs=0.1)
        assert "porta" in est2.nos

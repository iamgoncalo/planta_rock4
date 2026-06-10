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
    from app.services import secoes_mf, section_history, decision_log, rota_leve
    for mod in (fr, nc, secoes_mf, section_history, decision_log, rota_leve):
        mod.reset()
    yield
    for mod in (fr, nc, secoes_mf, section_history, decision_log, rota_leve):
        mod.reset()


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
        p = fr.ingest_cabecas("wc-01", "m", 30, fonte="prosegur", ts_ms=T0_MS, now_s=T0)
        assert p is not None
        assert p["ocupacao"] == 30.0
        assert p["idade_ancora_s"] == 0.0

    def test_trava_fisica_trunca_pico_500_macs(self):
        """Pico de 500 macs num minuto → truncado a n_acessos×40 + flag."""
        fr.ingest_wifi_bandas("wc-01", "m", "porta", 10, 0, ts_ms=T0_MS, now_s=T0)
        fr.ingest_cabecas("wc-01", "m", 10, fonte="prosegur",
                          ts_ms=T0_MS + 60_000, now_s=T0 + 60.0)
        p = fr.ingest_wifi_bandas("wc-01", "m", "porta", 500, 0,
                                  ts_ms=T0_MS + 120_000, now_s=T0 + 120.0)
        est = fr.get_estimador("wc-01_m")
        # 1 acesso × 40 p/min × 1 min = delta máximo 40 sobre a âncora (10)
        assert est.n_acessos == 1
        assert p["ocupacao"] == pytest.approx(50.0, abs=0.1)
        assert p["flag_anomalia"] is True

    def test_ocupacao_clamp_capacidade(self):
        """Estimativa nunca excede a capacidade da secção (clusters_geo)."""
        fr.ingest_wifi_bandas("wc-01", "f", "porta", 20, 0, ts_ms=T0_MS, now_s=T0)
        fr.ingest_cabecas("wc-01", "f", 60, ts_ms=T0_MS + 60_000, now_s=T0 + 60.0)
        ts = T0_MS + 120_000
        p = None
        for i in range(30):   # subida contínua → satura na capacidade
            p = fr.ingest_wifi_bandas("wc-01", "f", "porta", 20 + (i + 1) * 80,
                                      0, ts_ms=ts + i * 60_000, now_s=T0 + 120.0 + i * 60.0)
        est = fr.get_estimador("wc-01_f")
        assert est.capacidade == 63          # cap_f de WC-01 em clusters_geo
        assert p["ocupacao"] <= 63.0

    def test_decaimento_sem_nos(self):
        """0 nós online → decaimento exponencial com tau de 20 min."""
        fr.ingest_wifi_bandas("wc-02", "m", "porta", 30, 0, ts_ms=T0_MS, now_s=T0)
        fr.ingest_cabecas("wc-02", "m", 50, ts_ms=T0_MS + 1000, now_s=T0 + 1.0)
        # 20 min depois, nó stale (TTL 3 min) → occ ≈ 50/e
        p = fr.get_section_payload("wc-02_m", now_s=T0 + 1.0 + 20 * 60.0)
        assert p["nos_online"] == 0
        assert p["fonte_wifi"] == "offline"
        assert p["ocupacao"] == pytest.approx(50.0 / math.e, abs=1.0)

    def test_mediana_entre_nos_nao_media(self):
        """Agregação por mediana: outlier num nó não arrasta a secção."""
        est = fr.get_estimador("wc-03_m")
        fr.ingest_wifi_bandas("wc-03", "m", "porta", 10, 0, ts_ms=T0_MS, now_s=T0)
        fr.ingest_wifi_bandas("wc-03", "m", "meio", 12, 0, ts_ms=T0_MS, now_s=T0)
        fr.ingest_wifi_bandas("wc-03", "m", "fundo", 500, 0, ts_ms=T0_MS, now_s=T0)
        w = est.wifi_zona(T0, "macs_A")
        assert w == 12.0     # mediana(10, 12, 500) — a média seria 174

    def test_no_stale_sai_do_calculo(self):
        est = fr.get_estimador("wc-04_m")
        fr.ingest_wifi_bandas("wc-04", "m", "porta", 10, 0, ts_ms=T0_MS, now_s=T0)
        fr.ingest_wifi_bandas("wc-04", "m", "meio", 40, 0,
                              ts_ms=T0_MS + 240_000, now_s=T0 + 240.0)   # 4 min depois
        # "porta" não posta há 4 min → fora do TTL de 3 min
        assert est.wifi_zona(T0 + 240.0, "macs_A") == 40.0
        assert len(est._nos_online(T0 + 240.0)) == 1

    def test_fila_estimada_zona_b(self):
        """fila = a × mediana(macs_zona_B/k), com clamp à capacidade."""
        p = fr.ingest_wifi_bandas("wc-01", "m", "porta", 10, 20, ts_ms=T0_MS, now_s=T0)
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
        fr.ingest_wifi_bandas("wc-07", "m", node_id, 40, 0, ts_ms=T0_MS, now_s=T0)
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
        fr.ingest_wifi_bandas("wc-08", "m", "porta", 10, 0, ts_ms=T0_MS, now_s=T0)
        c = est.confianca_cruzada(T0)
        assert math.isfinite(c) and 0.0 <= c <= 1.0
        # wifi + âncora
        fr.ingest_cabecas("wc-08", "m", 12, ts_ms=T0_MS + 1000, now_s=T0 + 1.0)
        c = est.confianca_cruzada(T0 + 1.0)
        assert math.isfinite(c) and 0.0 < c <= 1.0
        # âncora muito antiga (c1 → 0)
        c = est.confianca_cruzada(T0 + 1e7)
        assert math.isfinite(c) and 0.0 <= c <= 1.0

    def test_ancora_fresca_e_nos_todos_online_da_confianca_alta(self):
        for pos in ("porta", "meio", "fundo"):
            fr.ingest_wifi_bandas("wc-01", "m", pos, 10, 0, ts_ms=T0_MS, now_s=T0)
        fr.ingest_cabecas("wc-01", "m", 12, fonte="prosegur",
                          ts_ms=T0_MS + 1000, now_s=T0 + 1.0)
        p = fr.get_section_payload("wc-01_m", now_s=T0 + 1.0)
        assert p["nos_online"] == 3
        assert 0.9 < p["confianca_cruzada"] <= 1.0

    def test_um_no_reduz_confianca(self):
        """1 nó online em 3 → c3 baixa → confiança reduzida vs 3 nós."""
        fr.ingest_wifi_bandas("wc-01", "m", "porta", 10, 0, ts_ms=T0_MS, now_s=T0)
        c_1no = fr.get_estimador("wc-01_m").confianca_cruzada(T0)
        for pos in ("porta", "meio", "fundo"):
            fr.ingest_wifi_bandas("wc-02", "m", pos, 10, 0, ts_ms=T0_MS, now_s=T0)
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
        cluster = r.json()["clusters"]["wc-01"]
        assert cluster["estado"] == "ok"   # contrato com /v2/sensors/fusion
        sec = cluster["seccoes"]["m"]
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
# Memória + orquestrador de demonstração
# ─────────────────────────────────────────────────────────────────────────────
class TestMemoriaEOrquestrador:
    def test_historia_grava_e_limita(self):
        """Cada ingestão grava um ponto; a memória é limitada a HISTORIA_MAX."""
        for i in range(900):
            fr.ingest_wifi_bandas("wc-01", "m", "porta", 10 + i % 5, 0,
                                  ts_ms=T0_MS + i * 60_000, now_s=T0 + i * 60.0)
        est = fr.get_estimador("wc-01_m")
        assert len(est.historia) == fr.HISTORIA_MAX
        pts = est.history(50)
        assert len(pts) == 50
        assert all(math.isfinite(p["conf"]) for p in pts)

    def test_payload_inclui_meta_da_regressao(self):
        fr.ingest_wifi_bandas("wc-01", "m", "porta", 10, 2, ts_ms=T0_MS, now_s=T0)
        p = fr.get_section_payload("wc-01_m", now_s=T0)
        for campo in ("r2", "b_actual", "pares_na_janela", "n_acessos",
                      "origem", "pontos_memoria", "surto_activo"):
            assert campo in p, f"falta {campo}"

    def test_demo_tick_alimenta_todas_as_seccoes(self):
        """Um tick do orquestrador alimenta as 14 secções com origem=simulado."""
        from app.services import fusao_rolante_demo as demo
        n = demo.demo_tick(T0)
        assert n == 14    # 6 MF × 2 + 2 UNI
        todos = fr.get_all(now_s=T0)
        assert len(todos) == 14
        for sid, p in todos.items():
            assert p["origem"] == "simulado", sid
            assert 0.0 <= p["ocupacao"] <= p["capacidade"], sid
            assert math.isfinite(p["confianca_cruzada"]), sid

    def test_demo_regressao_converge_para_a_verdade(self):
        """Com ticks suficientes (WiFi variável + cabeças), a aprende a_true."""
        from app.services import fusao_rolante_demo as demo
        for i in range(120):
            demo.demo_tick(T0 + i * demo.TICK_S)
        est = fr.get_estimador("wc-06")
        if est.regressao.fitted:    # var suficiente → fit aconteceu
            a_true = demo._a_true("wc-06")
            # a_eff esperado ≈ a_true / k_real_mediano do cluster (k_cal=1.0)
            assert fr.A_MIN <= est.regressao.a <= fr.A_MAX
            assert est.regressao.r2 > 0.5
            assert abs(est.regressao.a - a_true) / a_true < 0.6

    def test_demo_nao_toca_em_seccao_com_dados_reais(self):
        """Secção com ingestão REAL recente é intocável pelo orquestrador."""
        from app.services import fusao_rolante_demo as demo
        fr.ingest_cabecas("wc-01", "m", 33, fonte="prosegur",
                          ts_ms=T0_MS, origem="real", now_s=T0)
        demo.demo_tick(T0 + 10.0)
        p = fr.get_section_payload("wc-01_m", now_s=T0 + 10.0)
        assert p["origem"] == "real"
        # 33 menos o decaimento de 10s sem nós WiFi (sem contaminação simulada)
        assert p["ocupacao"] == pytest.approx(33.0, abs=0.5)

    @pytest.mark.asyncio
    async def test_endpoint_rolante_all_e_section(self, client):
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)
        # rota literal não é engolida por /fusion/{cluster_id}
        r = await client.get("/api/v1/fusion/rolante")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 14
        assert data["janela_pares"] == 36

        r = await client.get("/api/v1/fusion/rolante/wc-05?n=10")
        assert r.status_code == 200
        d = r.json()
        assert d["secao"] == "u"
        assert isinstance(d["historia"], list) and len(d["historia"]) >= 1
        assert isinstance(d["pares_regressao"], list)

        r = await client.get("/api/v1/fusion/rolante/wc-99")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_calibration_inclui_estado_vivo(self, client):
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)
        r = await client.get("/api/v1/calibration")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 40
        assert all("live" in n for n in data["nodes"])
        # nós alimentados pelo orquestrador têm contagens registadas
        com_dados = [n for n in data["nodes"] if n["live"]["macs_A"] is not None]
        assert len(com_dados) == 40


# ─────────────────────────────────────────────────────────────────────────────
# Snapshot — serialização round-trip + WARM START
# ─────────────────────────────────────────────────────────────────────────────
class TestSnapshot:
    def test_to_dict_restore_roundtrip(self):
        fr.ingest_wifi_bandas("wc-01", "m", "porta", 10, 2, ts_ms=T0_MS, now_s=T0)
        fr.ingest_cabecas("wc-01", "m", 15, fonte="prosegur",
                          ts_ms=T0_MS + 1000, now_s=T0 + 1.0)
        est = fr.get_estimador("wc-01_m")
        estado = est.to_dict()

        fr.reset()
        est2 = fr.get_estimador("wc-01_m")
        est2.restore(estado)
        assert est2.c_ultima == 15.0
        assert est2.tem_dados is True
        assert est2.ocupacao == pytest.approx(est.ocupacao or 15.0, abs=0.1)
        assert "porta" in est2.nos

    def test_warm_start_restaura_tudo_apos_restart_simulado(self):
        """MEMÓRIA: a_actual, âncora, filas e pares (w,c) sobrevivem ao restart."""
        # treina a regressão com dados variados + âncora + fila
        for i in range(12):
            fr.ingest_wifi_bandas("wc-02", "f", "porta", 10 + i * 6, 14,
                                  ts_ms=T0_MS + i * 60_000, now_s=T0 + i * 60.0)
            fr.ingest_cabecas("wc-02", "f", 8 + i * 3,
                              ts_ms=T0_MS + i * 60_000 + 1000, now_s=T0 + i * 60.0 + 1.0)
        est = fr.get_estimador("wc-02_f")
        antes = est.payload(T0 + 12 * 60.0)
        pares_antes = est.regression_pairs()
        assert len(pares_antes) >= 10

        # restart simulado: serializar tudo, destruir o processo lógico, restaurar
        snapshot = {sid: e.to_dict() for sid, e in fr._ESTIMADORES.items()}
        fr.reset()
        for sid, estado in snapshot.items():
            fr.get_estimador(sid).restore(estado)

        est2 = fr.get_estimador("wc-02_f")
        depois = est2.payload(T0 + 12 * 60.0)
        assert depois["a_actual"] == antes["a_actual"]
        assert depois["idade_ancora_s"] == antes["idade_ancora_s"]
        assert depois["fila_estimada"] == antes["fila_estimada"]
        assert est2.regression_pairs() == pares_antes   # nenhum par perdido
        assert len(est2.historia) == len(est.historia)  # memória intacta


# ─────────────────────────────────────────────────────────────────────────────
# Onda 6 — secções M/F, dwell, mulheres primeiro
# ─────────────────────────────────────────────────────────────────────────────
class TestSecoesMF:
    def test_espera_f_maior_que_m_com_filas_iguais(self):
        """Dwell F=3.6 > M=2.0 ⇒ a mesma fila espera mais no F."""
        from app.services import secoes_mf
        fila = 300.0
        # WC-03: 54 M / 48 F — normaliza por posições para isolar o dwell
        em = secoes_mf.espera_prevista_min("wc-03_m", fila)
        ef = secoes_mf.espera_prevista_min("wc-03_f", fila)
        assert ef > em
        # razão esperada = (dwell_f/pos_f)/(dwell_m/pos_m), tolerante a arredondamento
        assert ef / em == pytest.approx((3.6 / 48) / (2.0 / 54), rel=0.02)

    def test_pedido_f_nunca_ve_seccao_m(self):
        from app.services import secoes_mf
        sf = secoes_mf.seccoes_permitidas("f")
        sm = secoes_mf.seccoes_permitidas("m")
        assert all(not s.endswith("_m") for s in sf)
        assert all(not s.endswith("_f") for s in sm)
        # unissexo presente nos dois (válvula feminina)
        assert {"wc-05", "wc-06"} <= set(sf) and {"wc-05", "wc-06"} <= set(sm)

    def test_regra_wc05_usa_interior_mais_fila(self):
        """(interior+fila) > 0.85×(cap+espera) — NUNCA só interior."""
        from app.services import secoes_mf
        # cap=133, espera=106.4 → limite = 0.85×239.4 = 203.49
        assert secoes_mf.wc05_bloquear_steward(133.0, 0.0) is False  # só interior NUNCA dispara
        assert secoes_mf.wc05_bloquear_steward(130.0, 80.0) is True
        assert secoes_mf.wc05_bloquear_steward(100.0, 100.0) is False  # 200 < 203.49

    def test_queue_cap_do_seed(self):
        from app.services import secoes_mf
        # WC-01: espera 81, posições 72M/63F (135) → quota proporcional
        assert secoes_mf.queue_cap("wc-01_m") == pytest.approx(81 * 72 / 135, abs=0.1)
        assert secoes_mf.queue_cap("wc-05") == pytest.approx(106.4, abs=0.1)

    def test_alertas_warn_e_crit(self):
        from app.services import secoes_mf
        qc = secoes_mf.queue_cap("wc-04_f")
        assert secoes_mf.alerta_fila("wc-04_f", qc * 0.5) is None
        assert secoes_mf.alerta_fila("wc-04_f", qc * 0.8) == "WARN"
        assert secoes_mf.alerta_fila("wc-04_f", qc * 1.0) == "CRIT"

    def test_cluster_fechado_auditado_e_excluido(self):
        """decision_log regista com utilizador+ts; encaminhamento exclui."""
        from app.services import secoes_mf, decision_log
        secoes_mf.set_fechado("wc-06", True, "matheus", "inundação simulada")
        assert secoes_mf.is_fechado("wc-06")
        assert "wc-06" not in secoes_mf.seccoes_permitidas("f")
        assert secoes_mf.servico_pmin("wc-06") == 0.0
        assert secoes_mf.espera_prevista_min("wc-06", 10) == 999.0
        regs = decision_log.query(tipo="cluster_fechado")
        assert len(regs) == 1
        assert regs[0]["utilizador"] == "matheus"
        assert regs[0]["ts_ms"] > 0
        assert regs[0]["antes"]["fechado"] is False
        assert regs[0]["depois"]["fechado"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Onda 5 — section_history + replay
# ─────────────────────────────────────────────────────────────────────────────
class TestSectionHistory:
    def test_grava_1_por_minuto_e_pagina(self):
        from app.services import section_history as sh
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)
        # 6 minutos de registos (force bypassa o relógio real)
        for i in range(6):
            n = sh.record_minute(T0 + i * 60.0, force=True)
            assert n == 14
        # dentro do mesmo minuto NÃO duplica
        assert sh.record_minute(T0 + 5 * 60.0) == 0
        page = sh.query("wc-05", page=1, size=4)
        assert page["total"] == 6
        assert page["pages"] == 2
        assert len(page["registos"]) == 4
        r = page["registos"][0]
        for campo in ("ts_ms", "ocupacao", "fila", "espera_prevista_min",
                      "confianca", "a_actual", "alertas"):
            assert campo in r

    def test_replay_em_blocos_de_10_min(self):
        from app.services import section_history as sh
        from app.services import fusao_rolante_demo as demo
        from datetime import datetime, timezone
        dia0 = datetime(2025, 6, 15, tzinfo=timezone.utc).timestamp()
        demo.demo_tick(dia0)
        for i in range(35):   # 35 min → blocos 0,1,2,3
            sh.record_minute(dia0 + i * 60.0, force=True)
        rep = sh.replay_dia("2025-06-15")
        assert rep["bloco_min"] == 10
        assert rep["total_seccoes"] == 14
        serie = rep["seccoes"]["wc-06"]
        assert [b["bloco"] for b in serie] == [0, 1, 2, 3]
        assert serie[0]["amostras"] == 10

    @pytest.mark.asyncio
    async def test_endpoints_history_e_replay(self, client):
        from app.services import section_history as sh
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)
        for i in range(5):
            sh.record_minute(T0 + i * 60.0, force=True)
        r = await client.get("/api/v1/history/wc-01_m?size=3")
        assert r.status_code == 200
        assert r.json()["total"] == 5
        r = await client.get("/api/v1/history/wc-99")
        assert r.status_code == 404
        r = await client.get("/api/v1/history/replay?dia=not-a-date")
        assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# Onda 8 — rota mais leve (Dijkstra, género, histerese, fecho)
# ─────────────────────────────────────────────────────────────────────────────
class TestRotaLeve:
    def test_dijkstra_usa_grafo_com_vizinhancas_confirmadas(self):
        from app.services import rota_leve
        walk = rota_leve.dijkstra_min("WC-01")
        assert walk["WC-01"] == 0.0
        # WC-08 é vizinho directo de WC-01 (confirmado) — 1 salto
        from app.clusters_geo import distance_m
        assert walk["WC-08"] == pytest.approx(distance_m("WC-01", "WC-08") / 70.0, abs=0.1)
        assert walk["WC-02"] == pytest.approx(distance_m("WC-01", "WC-02") / 70.0, abs=0.1)
        # todos os clusters alcançáveis
        assert len(walk) == 8

    def test_route_respeita_genero_e_custo_decomposto(self):
        from app.services import rota_leve
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)
        r = rota_leve.compute_route("ENTRADA", "f", now_s=T0)
        assert 1 <= len(r["opcoes"]) <= 3
        for o in r["opcoes"]:
            assert not o["wc"].endswith("_m")   # F NUNCA vê secções M
            for campo in ("wc", "tipo", "caminhada_min", "fila_min",
                          "congestao", "surto", "confianca", "total_min",
                          "quota_pct"):
                assert campo in o
        # anti-manada: as quotas não são 100/0/0
        if len(r["opcoes"]) > 1:
            assert r["opcoes"][0]["quota_pct"] < 100.0
        assert r["narrativa"]["pt"] and r["narrativa"]["en"]

    def test_histerese_impede_flip_flop(self):
        from app.services import rota_leve, secoes_mf
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)
        r1 = rota_leve.compute_route("WC-03", "m", now_s=T0)
        rec1 = r1["recomendado"]
        # pequena perturbação: fila ligeira no recomendado (ganho <20%)
        est = fr.get_estimador(rec1)
        est.fila_estimada = min(est.fila_estimada + 3.0,
                                secoes_mf.queue_cap(rec1) * 1.4)
        r2 = rota_leve.compute_route("WC-03", "m", now_s=T0 + 30.0)
        assert r2["recomendado"] == rec1     # não troca: ganho pequeno e <3 min
        assert r2["recomendado_desde_s"] >= 30.0

    def test_route_exclui_cluster_fechado_no_mesmo_tick(self):
        from app.services import rota_leve, secoes_mf
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)
        r1 = rota_leve.compute_route("PALCO_MUNDO", "f", now_s=T0)
        alvo = r1["recomendado"].split("_")[0]
        secoes_mf.set_fechado(alvo, True, "ricardo", "teste de fecho")
        rota_leve.reset()   # o PUT real faz isto — cache e histerese caem já
        r2 = rota_leve.compute_route("PALCO_MUNDO", "f", now_s=T0 + 1.0)
        assert all(not o["wc"].startswith(alvo) for o in r2["opcoes"])

    @pytest.mark.asyncio
    async def test_endpoint_route_e_estado(self, client):
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)
        r = await client.get("/api/v1/route?origem=ENTRADA&genero=f")
        assert r.status_code == 200
        assert r.json()["recomendado"] is not None
        r = await client.get("/api/v1/route?origem=NARNIA&genero=f")
        assert r.status_code == 422
        # fechar cluster por API, auditado
        r = await client.put("/api/v1/sections/wc-06/estado", json={
            "fechado": True, "utilizador": "goncalo", "justificacao": "drill",
        })
        assert r.status_code == 200
        assert r.json()["estado"]["fechado"] is True
        r = await client.get("/api/v1/decisions?tipo=cluster_fechado")
        assert r.json()["total"] == 1
        r = await client.get("/api/v1/route?origem=ENTRADA&genero=f")
        assert all(not o["wc"].startswith("wc-06") for o in r.json()["opcoes"])


# ─────────────────────────────────────────────────────────────────────────────
# S24 (quarentena de nó) + S25 (ts_suspeito — relógio errado)
# ─────────────────────────────────────────────────────────────────────────────
class TestQuarentenaETs:
    def test_no_com_vies_entra_em_quarentena_e_sai_da_mediana(self):
        """3 nós (dois ~10, um ~500) durante 11 min a 60s: o nó mentiroso
        (|z| > 3 com desvio robusto 1.4826×MAD) entra em quarentena, sai da
        agregação wifi_zona e fica registado no decision_log."""
        from app.services import decision_log
        for i in range(12):                      # 0..11 min, cadência 60s
            ts = T0_MS + i * 60_000
            agora = T0 + i * 60.0
            fr.ingest_wifi_bandas("wc-01", "m", "porta", 10, 0,
                                  ts_ms=ts, now_s=agora)
            fr.ingest_wifi_bandas("wc-01", "m", "meio", 11, 0,
                                  ts_ms=ts, now_s=agora)
            fr.ingest_wifi_bandas("wc-01", "m", "fundo", 500, 0,
                                  ts_ms=ts, now_s=agora)
        est = fr.get_estimador("wc-01_m")
        assert "fundo" in est.quarentena
        # exposto no payload
        p = fr.get_section_payload("wc-01_m", now_s=T0 + 11 * 60.0)
        assert p["nos_quarentena"] == ["fundo"]
        # nó em quarentena sai da agregação: mediana só entre porta/meio
        assert est.wifi_zona(T0 + 11 * 60.0, "macs_A") == pytest.approx(10.5)
        # rasto no decision_log (origem=motor, uma única entrada)
        regs = decision_log.query(tipo="quarentena_no")
        assert len(regs) == 1
        assert regs[0]["origem"] == "motor"
        assert regs[0]["seccao"] == "wc-01_m"
        assert regs[0]["depois"]["no"] == "fundo"
        assert regs[0]["depois"]["z"] > 3.0

    def test_desvio_curto_nao_quarentena(self):
        """Desvio com menos de 10 min de persistência NÃO quarentena."""
        for i in range(5):                       # só 4 min de desvio
            ts = T0_MS + i * 60_000
            agora = T0 + i * 60.0
            fr.ingest_wifi_bandas("wc-02", "m", "porta", 10, 0,
                                  ts_ms=ts, now_s=agora)
            fr.ingest_wifi_bandas("wc-02", "m", "meio", 11, 0,
                                  ts_ms=ts, now_s=agora)
            fr.ingest_wifi_bandas("wc-02", "m", "fundo", 500, 0,
                                  ts_ms=ts, now_s=agora)
        est = fr.get_estimador("wc-02_m")
        assert est.quarentena == set()
        assert "fundo" in est.primeiro_desvio_ts   # desvio em acompanhamento

    def test_remover_quarentena_exige_e_regista_utilizador(self):
        """PROIBIDO sair de quarentena sem registo: utilizador obrigatório e
        decision_log (tipo=quarentena_removida, origem=operador) sempre."""
        from app.services import decision_log
        est = fr.get_estimador("wc-03_m")
        est.quarentena.add("fundo")
        # sem utilizador → recusado e o nó continua em quarentena
        with pytest.raises(ValueError):
            fr.remover_quarentena("wc-03_m", "fundo", "")
        with pytest.raises(ValueError):
            fr.remover_quarentena("wc-03_m", "fundo", "   ")
        assert "fundo" in est.quarentena
        assert decision_log.query(tipo="quarentena_removida") == []
        # com utilizador → remove E regista
        out = fr.remover_quarentena("wc-03_m", "fundo", "matheus")
        assert out["removido"] is True
        assert "fundo" not in est.quarentena
        regs = decision_log.query(tipo="quarentena_removida")
        assert len(regs) == 1
        assert regs[0]["utilizador"] == "matheus"
        assert regs[0]["origem"] == "operador"
        assert regs[0]["seccao"] == "wc-03_m"

    def test_quarentena_persiste_no_snapshot(self):
        est = fr.get_estimador("wc-04_m")
        est.quarentena.add("meio")
        estado = est.to_dict()
        fr.reset()
        est2 = fr.get_estimador("wc-04_m")
        est2.restore(estado)
        assert "meio" in est2.quarentena

    def test_ts_futuro_nao_contamina_e_aparece_em_ts_suspeitos(self):
        """Nó/âncora com relógio 10 min no futuro: aceite, marcado, NÃO funde
        — a regressão e a ocupação ficam intactas até chegar ts são."""
        # estado são: 2 nós + âncora fresca
        for pos in ("porta", "meio"):
            fr.ingest_wifi_bandas("wc-07", "m", pos, 10, 0,
                                  ts_ms=T0_MS, now_s=T0)
        fr.ingest_cabecas("wc-07", "m", 20, fonte="prosegur",
                          ts_ms=T0_MS + 1000, now_s=T0 + 1.0)
        est = fr.get_estimador("wc-07_m")
        pares_antes = len(est.regressao.pares)
        occ_antes = est.ocupacao
        # nó com ts 10 min no futuro → marcado, fora da mediana, occ intacta
        p = fr.ingest_wifi_bandas("wc-07", "m", "fundo", 400, 0,
                                  ts_ms=T0_MS + 600_000, now_s=T0 + 1.0)
        assert est.nos["fundo"]["ts_suspeito"] is True
        assert "fundo" in p["ts_suspeitos"]
        assert est.wifi_zona(T0 + 1.0, "macs_A") == pytest.approx(10.0)
        assert est.ocupacao == pytest.approx(occ_antes, abs=0.1)
        assert len(est.regressao.pares) == pares_antes
        # âncora com ts 10 min no futuro → não cria par nem re-baseia
        p = fr.ingest_cabecas("wc-07", "m", 999, fonte="luxonis",
                              ts_ms=T0_MS + 600_000, now_s=T0 + 2.0)
        assert len(est.regressao.pares) == pares_antes
        assert est.c_ultima == 20.0
        assert est.ocupacao == pytest.approx(occ_antes, abs=0.1)
        assert "ancora" in p["ts_suspeitos"] and "fundo" in p["ts_suspeitos"]
        # chega ts são → o nó volta a fundir e sai de ts_suspeitos
        fr.ingest_wifi_bandas("wc-07", "m", "fundo", 12, 0,
                              ts_ms=T0_MS + 120_000, now_s=T0 + 120.0)
        assert est.nos["fundo"]["ts_suspeito"] is False
        p = fr.get_section_payload("wc-07_m", now_s=T0 + 120.0)
        assert "fundo" not in p["ts_suspeitos"]


# ─────────────────────────────────────────────────────────────────────────────
# Idempotência do ingest
# ─────────────────────────────────────────────────────────────────────────────
class TestIdempotencia:
    def test_mesmo_no_mesmo_ts_conta_uma_vez(self):
        fr.ingest_cabecas("wc-01", "m", 10, ts_ms=T0_MS, now_s=T0)
        p1 = fr.ingest_wifi_bandas("wc-01", "m", "porta", 50, 5,
                                   ts_ms=T0_MS + 60_000, now_s=T0 + 60.0)
        est = fr.get_estimador("wc-01_m")
        hist_len = len(est.historia)
        # repetição exacta (mesmo nó + mesmo ts) é ignorada por inteiro
        p2 = fr.ingest_wifi_bandas("wc-01", "m", "porta", 50, 5,
                                   ts_ms=T0_MS + 60_000, now_s=T0 + 60.0)
        assert len(est.historia) == hist_len
        assert p2["ocupacao"] == p1["ocupacao"]

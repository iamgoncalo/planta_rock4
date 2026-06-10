"""
Testes do AMBIENTE operacional (app/services/ambiente.py + routers/ambiente.py).

Cobre (mínimo exigido):
  - S01: chuva activa ⇒ dwell ×1.4 no servico_pmin + decision_log com antes/depois
  - S02: aresta em lama muda o top-3 vs sem lama; pcd=True NUNCA usa a aresta
  - flag off reverte os efeitos e fecha o evento no EVENT_LOG
  - S03: chuva activa >60 min ⇒ lama generalizada em todas as arestas (reversível)
  - S04: calor >30 °C sobe o procura_factor (×1.15; ×1.38 com chuva)
  - S05: evacuação em bloco fecha N clusters e /route exclui-os no mesmo tick
  - S09: corte de ENTRADA|WC-05 gera alternativa que não usa a aresta
  - 422 JSON em flag/aresta/estado/cluster inválidos e lista vazia
"""
from __future__ import annotations

import time

import pytest

from app.clusters_geo import distance_m
from app.services import ambiente, rota_leve, secoes_mf

# Base temporal sintética (fora de qualquer janela de surto pós-show)
T0 = 1_750_000_000.0
VEL = rota_leve.VELOCIDADE_M_MIN          # 70 m/min em piso normal
VEL_LAMA = VEL * ambiente.FACTOR_LAMA     # ≈46.7 m/min em lama


@pytest.fixture(autouse=True)
def _estado_limpo():
    """Cada teste parte de ambiente, secções, rotas e fusão virgens."""
    from app.services import decision_log, fusao_rolante, node_calibration
    mods = (ambiente, fusao_rolante, node_calibration, secoes_mf,
            decision_log, rota_leve)
    for m in mods:
        m.reset()
    yield
    for m in mods:
        m.reset()


# ─────────────────────────────────────────────────────────────────────────────
# S01 — chuva: dwell ×1.4 + auditoria
# ─────────────────────────────────────────────────────────────────────────────
class TestChuva:
    @pytest.mark.asyncio
    async def test_chuva_sobe_dwell_14_e_audita(self, client):
        """PUT chuva → servico_pmin cai ×1.4 (dwell sobe) + decision_log."""
        from app.services import decision_log
        antes = secoes_mf.servico_pmin("wc-03_f")     # 48 / 3.6
        r = await client.put("/api/v1/ambiente/chuva", json={
            "activo": True, "intensidade": "forte",
            "utilizador": "matheus", "justificacao": "aguaceiro real",
        })
        assert r.status_code == 200, r.text
        assert r.json()["estado"]["activa"] is True
        assert ambiente.dwell_factor() == pytest.approx(1.4)
        depois = secoes_mf.servico_pmin("wc-03_f")    # 48 / (3.6×1.4)
        assert antes / depois == pytest.approx(1.4, rel=0.001)
        # procura também sobe ×1.2 com chuva
        assert ambiente.procura_factor() == pytest.approx(1.2)
        # auditoria: decision_log com utilizador + antes/depois
        regs = decision_log.query(tipo="ambiente_chuva")
        assert len(regs) == 1
        assert regs[0]["utilizador"] == "matheus"
        assert regs[0]["antes"]["activa"] is False
        assert regs[0]["depois"]["activa"] is True
        assert regs[0]["depois"]["intensidade"] == "forte"

    @pytest.mark.asyncio
    async def test_flag_off_reverte_e_fecha_evento(self, client):
        """Desligar a chuva reverte dwell/procura e fecha o evento aberto."""
        ambiente.set_flag("chuva", True, "matheus")
        assert ambiente.dwell_factor() == pytest.approx(1.4)
        r = await client.put("/api/v1/ambiente/chuva", json={
            "activo": False, "utilizador": "matheus",
        })
        assert r.status_code == 200
        assert ambiente.dwell_factor() == 1.0
        assert ambiente.procura_factor() == 1.0
        # EVENT_LOG: o evento aberto fica fechado (fim_ts preenchido)
        r = await client.get("/api/v1/ambiente/eventos")
        assert r.status_code == 200
        evs = r.json()["eventos"]
        assert len(evs) == 1
        assert evs[0]["flag"] == "chuva"
        assert evs[0]["inicio_ts"] is not None
        assert evs[0]["fim_ts"] is not None
        # estado completo reflecte o off
        r = await client.get("/api/v1/ambiente")
        d = r.json()
        assert d["chuva"]["activa"] is False
        assert d["dwell_factor"] == 1.0


# ─────────────────────────────────────────────────────────────────────────────
# S02 — lama por aresta: top-3 muda; PCD nunca usa a aresta
# ─────────────────────────────────────────────────────────────────────────────
class TestLamaAresta:
    def test_lama_muda_top3_e_pcd_evita_a_aresta(self):
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)
        base = rota_leve.dijkstra_min("WC-08")
        d_direct = distance_m("WC-01", "WC-08")
        assert base["WC-01"] == pytest.approx(d_direct / VEL, abs=0.1)
        r_sem = rota_leve.compute_route("WC-08", "f", now_s=T0)
        cam_sem = {o["wc"]: o["caminhada_min"] for o in r_sem["opcoes"]}

        # lama nas duas saídas de WC-08 (ids canónicos "A|B" ordenados)
        ambiente.set_aresta_estado("WC-01|WC-08", "lama", "matheus", "poça")
        ambiente.set_aresta_estado("WC-06|WC-08", "lama", "matheus", "poça")
        rota_leve.reset()   # o PUT real faz isto — cache cai no mesmo tick

        # caminhada sobe (lama ⇒ ~46.7 m/min em vez de 70); o motor pode
        # preferir um desvio misto (1 aresta lama + normais) ao directo todo
        # em lama — nunca pior do que o directo em lama
        walk = rota_leve.dijkstra_min("WC-08")
        assert walk["WC-01"] > base["WC-01"]
        assert walk["WC-01"] <= d_direct / VEL_LAMA + 0.1

        # top-3 reflecte a lama: nenhuma caminhada desce e pelo menos uma
        # sobe (desvios por landmarks podem absorver parte do efeito)
        r_com = rota_leve.compute_route("WC-08", "f", now_s=T0 + 1.0)
        cam_com = {o["wc"]: o["caminhada_min"] for o in r_com["opcoes"]}
        comuns = set(cam_sem) & set(cam_com)
        assert all(cam_com[wc] >= cam_sem[wc] for wc in comuns)
        assert (any(cam_com[wc] > cam_sem[wc] for wc in comuns)
                or set(cam_sem) != set(cam_com))

        # pcd=True NUNCA passa por lama: igual a excluir a aresta do grafo
        ambiente.set_aresta_estado("WC-06|WC-08", "normal", "matheus")
        ambiente.set_aresta_estado("WC-01|WC-08", "cortada", "matheus")
        d_sem_aresta = rota_leve.dijkstra_min("WC-08")["WC-01"]
        ambiente.set_aresta_estado("WC-01|WC-08", "lama", "matheus")
        walk_pcd = rota_leve.dijkstra_min("WC-08", pcd=True)
        assert walk_pcd["WC-01"] == pytest.approx(d_sem_aresta, abs=0.1)
        assert walk_pcd["WC-01"] > base["WC-01"]
        # e o /route com pcd devolve essas caminhadas (cache key inclui pcd)
        r_pcd = rota_leve.compute_route("WC-08", "f", now_s=T0 + 2.0, pcd=True)
        assert r_pcd["pcd"] is True

    @pytest.mark.asyncio
    async def test_get_arestas_expoe_estado(self, client):
        await client.put("/api/v1/flow/aresta/WC-01|WC-08/estado", json={
            "estado": "lama", "utilizador": "matheus",
        })
        r = await client.get("/api/v1/flow/arestas")
        assert r.status_code == 200
        d = r.json()
        assert d["total"] == 18
        assert d["arestas"]["WC-01|WC-08"]["estado"] == "lama"
        assert d["arestas"]["WC-01|WC-08"]["lama_efectiva"] is True
        assert d["arestas"]["WC-01|WC-02"]["estado"] == "normal"


# ─────────────────────────────────────────────────────────────────────────────
# S03 — chuva >60 min ⇒ lama generalizada (reversível)
# ─────────────────────────────────────────────────────────────────────────────
class TestLamaGeneralizada:
    def test_chuva_60min_generaliza_lama_e_reverte(self):
        ambiente.set_flag("chuva", True, "matheus")
        assert ambiente.lama_generalizada() is False
        # manipula desde_ts: a chover há 70 min
        with ambiente._LOCK:
            ambiente._ESTADO["chuva"]["desde_ts"] = time.time() - 70 * 60.0
        assert ambiente.lama_generalizada() is True
        assert ambiente.arestas_em_lama() == ambiente.arestas_validas()
        assert ambiente.estado_arestas()["lama_generalizada"] is True
        # toda a caminhada abranda para a velocidade de lama
        d = distance_m("WC-01", "WC-02")
        walk = rota_leve.dijkstra_min("WC-01")
        assert walk["WC-02"] == pytest.approx(d / VEL_LAMA, abs=0.2)
        # REVERSÍVEL: chuva off ⇒ lama generalizada cai
        ambiente.set_flag("chuva", False, "matheus")
        assert ambiente.lama_generalizada() is False
        assert ambiente.arestas_em_lama() == set()
        walk = rota_leve.dijkstra_min("WC-01")
        assert walk["WC-02"] == pytest.approx(d / VEL, abs=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# S04 — calor >30 °C sobe a procura
# ─────────────────────────────────────────────────────────────────────────────
class TestCalor:
    @pytest.mark.asyncio
    async def test_calor_sobe_procura_factor(self, client):
        r = await client.put("/api/v1/ambiente/calor", json={
            "activo": True, "temp_c": 32.0, "utilizador": "ricardo",
        })
        assert r.status_code == 200
        assert ambiente.procura_factor() == pytest.approx(1.15)
        # calor NÃO mexe no dwell (efeito canónico é só na procura)
        assert ambiente.dwell_factor() == 1.0
        # com chuva em simultâneo: 1.2 × 1.15 = 1.38
        ambiente.set_flag("chuva", True, "ricardo")
        assert ambiente.procura_factor() == pytest.approx(1.38)
        # calor ≤30 °C não conta
        ambiente.set_flag("chuva", False, "ricardo")
        ambiente.set_flag("calor", True, "ricardo", temp_c=28.0)
        assert ambiente.procura_factor() == 1.0
        # exposto no GET /api/v1/ambiente
        r = await client.get("/api/v1/ambiente")
        assert r.json()["calor"]["temp_c"] == 28.0


# ─────────────────────────────────────────────────────────────────────────────
# S05 — evacuação em bloco
# ─────────────────────────────────────────────────────────────────────────────
class TestEvacuacao:
    @pytest.mark.asyncio
    async def test_evacuacao_fecha_clusters_e_route_exclui(self, client):
        from app.services import decision_log
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)
        r = await client.post("/api/v1/ambiente/evacuacao", json={
            "clusters": ["wc-01", "wc-06"], "utilizador": "ricardo",
            "justificacao": "drill de evacuação norte",
        })
        assert r.status_code == 200, r.text
        assert r.json()["clusters"] == ["wc-01", "wc-06"]
        assert secoes_mf.is_fechado("wc-01") and secoes_mf.is_fechado("wc-06")
        # auditoria própria tipo=evacuacao (além dos cluster_fechado)
        regs = decision_log.query(tipo="evacuacao")
        assert len(regs) == 1
        assert regs[0]["utilizador"] == "ricardo"
        assert regs[0]["depois"]["clusters"] == ["wc-01", "wc-06"]
        assert decision_log.query(tipo="cluster_fechado", limit=10)
        # /route exclui os evacuados NO MESMO TICK (cache caiu)
        r = await client.get("/api/v1/route?origem=ENTRADA&genero=f")
        assert r.status_code == 200
        for o in r.json()["opcoes"]:
            assert not o["wc"].startswith("wc-01")
            assert not o["wc"].startswith("wc-06")


# ─────────────────────────────────────────────────────────────────────────────
# S09 — corte de aresta gera alternativa
# ─────────────────────────────────────────────────────────────────────────────
class TestCorteAresta:
    @pytest.mark.asyncio
    async def test_corte_entrada_wc05_gera_alternativa(self, client):
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)
        base = rota_leve.dijkstra_min("ENTRADA")["WC-05"]
        r = await client.put("/api/v1/flow/aresta/ENTRADA|WC-05/estado", json={
            "estado": "cortada", "utilizador": "matheus",
            "justificacao": "vedação caída",
        })
        assert r.status_code == 200, r.text
        assert r.json()["estado"] == "cortada"
        # a alternativa NÃO usa a aresta cortada: vai por ENTRADA→WC-03→WC-05
        alt = (rota_leve._dist("ENTRADA", "WC-03")
               + distance_m("WC-03", "WC-05")) / VEL
        walk = rota_leve.dijkstra_min("ENTRADA")
        assert walk["WC-05"] > base
        assert walk["WC-05"] == pytest.approx(alt, abs=0.1)
        # /route continua a responder com recomendação válida
        r = await client.get("/api/v1/route?origem=ENTRADA&genero=f")
        assert r.status_code == 200
        assert r.json()["recomendado"] is not None
        # reversível: normal repõe o caminho directo
        r = await client.put("/api/v1/flow/aresta/ENTRADA|WC-05/estado", json={
            "estado": "normal", "utilizador": "matheus",
        })
        assert r.status_code == 200
        assert rota_leve.dijkstra_min("ENTRADA")["WC-05"] == pytest.approx(
            base, abs=0.1)


# ─────────────────────────────────────────────────────────────────────────────
# 422 — erros sempre JSON
# ─────────────────────────────────────────────────────────────────────────────
class Test422:
    @pytest.mark.asyncio
    async def test_422_flag_aresta_estado_e_evacuacao(self, client):
        casos = [
            # flag desconhecida
            ("put", "/api/v1/ambiente/granizo",
             {"activo": True, "utilizador": "matheus"}),
            # utilizador demasiado curto (min 2)
            ("put", "/api/v1/ambiente/chuva",
             {"activo": True, "utilizador": "x"}),
            # aresta inexistente no grafo (WC-01 e WC-07 não são vizinhos)
            ("put", "/api/v1/flow/aresta/WC-01|WC-07/estado",
             {"estado": "lama", "utilizador": "matheus"}),
            # estado de aresta inválido
            ("put", "/api/v1/flow/aresta/WC-01|WC-08/estado",
             {"estado": "gelo", "utilizador": "matheus"}),
            # evacuação: lista vazia
            ("post", "/api/v1/ambiente/evacuacao",
             {"clusters": [], "utilizador": "ricardo",
              "justificacao": "drill"}),
            # evacuação: cluster desconhecido
            ("post", "/api/v1/ambiente/evacuacao",
             {"clusters": ["wc-99"], "utilizador": "ricardo",
              "justificacao": "drill"}),
        ]
        for metodo, url, body in casos:
            r = await getattr(client, metodo)(url, json=body)
            assert r.status_code == 422, f"{url} → {r.status_code}: {r.text}"
            assert "application/json" in r.headers["content-type"]
        # nada ficou fechado nem marcado pelos pedidos inválidos
        assert secoes_mf.estado_fechados() == {}
        assert ambiente.arestas_em_lama() == set()

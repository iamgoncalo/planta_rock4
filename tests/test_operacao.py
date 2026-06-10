"""
Testes de operação (onda 9): limpeza por secção (S07), modo saída (S19),
flag de congestão parado-vs-fluir (S20) e heartbeat dos gateways (S11).
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.services import fusao_rolante as fr
from app.services import gateways_hb
from app.services import node_calibration as nc

# Base temporal sintética (fora de qualquer janela de surto pós-show)
T0 = 1_750_000_000.0
T0_MS = int(T0 * 1000)


@pytest.fixture(autouse=True)
def _estado_limpo():
    """Cada teste parte de estado virgem (padrão de test_fusao_rolante)."""
    from app.services import secoes_mf, section_history, decision_log, rota_leve
    mods = (fr, nc, secoes_mf, section_history, decision_log, rota_leve,
            gateways_hb)
    for mod in mods:
        mod.reset()
    yield
    for mod in mods:
        mod.reset()


def _show_terminado(delta_s: float):
    """Show sintético terminado há delta_s segundos (relativo a T0)."""
    end_iso = datetime.fromtimestamp(T0 - delta_s, tz=timezone.utc).isoformat()
    start_iso = datetime.fromtimestamp(T0 - delta_s - 5400.0,
                                       tz=timezone.utc).isoformat()
    return SimpleNamespace(show_id="show_sintetico", name="Sintético",
                           stage="Palco Mundo", start_iso=start_iso,
                           end_iso=end_iso, headliner=True,
                           expected_surge_pct=80.0)


# ─────────────────────────────────────────────────────────────────────────────
# S07 — secção em limpeza
# ─────────────────────────────────────────────────────────────────────────────
class TestSeccaoLimpeza:
    @pytest.mark.asyncio
    async def test_limpeza_so_afecta_a_propria_seccao(self, client):
        """WC-04_F em limpeza NÃO afecta WC-04_M; sai do route e fica CRIT."""
        from app.services import secoes_mf, decision_log
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)

        r = await client.put("/api/v1/sections/wc-04_f/estado", json={
            "em_limpeza": True, "eta_min": 12,
            "utilizador": "matheus", "justificacao": "turno de limpeza",
        })
        assert r.status_code == 200, r.text
        assert r.json()["limpeza"]["em_limpeza"] is True
        assert r.json()["limpeza"]["eta_min"] == 12

        # só ESSA secção: a irmã M continua viva
        assert secoes_mf.is_em_limpeza("wc-04_f") is True
        assert secoes_mf.is_em_limpeza("wc-04_m") is False
        assert "wc-04_f" not in secoes_mf.seccoes_permitidas("f")
        assert "wc-04_m" in secoes_mf.seccoes_permitidas("m")
        assert secoes_mf.servico_pmin("wc-04_f") == 0.0
        assert secoes_mf.servico_pmin("wc-04_m") > 0.0
        assert secoes_mf.alerta_fila("wc-04_f", 0.0) == "CRIT"

        # route F nunca propõe a secção em limpeza
        r = await client.get("/api/v1/route?origem=ENTRADA&genero=f")
        assert r.status_code == 200
        assert all(o["wc"] != "wc-04_f" for o in r.json()["opcoes"])

        # auditado + exposto com eta no GET /sections/estado
        regs = decision_log.query(tipo="seccao_limpeza")
        assert len(regs) == 1 and regs[0]["seccao"] == "wc-04_f"
        assert regs[0]["utilizador"] == "matheus"
        r = await client.get("/api/v1/sections/estado")
        limp = r.json()["limpezas"]["wc-04_f"]
        assert limp["em_limpeza"] is True and limp["eta_min"] == 12

    @pytest.mark.asyncio
    async def test_reabertura_reverte_tudo(self, client):
        from app.services import secoes_mf, decision_log
        secoes_mf.set_limpeza("wc-04_f", True, 10, "matheus", "limpeza")
        assert "wc-04_f" not in secoes_mf.seccoes_permitidas("f")

        r = await client.put("/api/v1/sections/wc-04_f/estado", json={
            "em_limpeza": False, "utilizador": "matheus",
            "justificacao": "limpeza concluída",
        })
        assert r.status_code == 200, r.text
        assert secoes_mf.is_em_limpeza("wc-04_f") is False
        assert "wc-04_f" in secoes_mf.seccoes_permitidas("f")
        assert secoes_mf.servico_pmin("wc-04_f") > 0.0
        assert secoes_mf.alerta_fila("wc-04_f", 0.0) is None
        assert len(decision_log.query(tipo="seccao_reaberta")) == 1


# ─────────────────────────────────────────────────────────────────────────────
# S19 — modo saída (fim do último show)
# ─────────────────────────────────────────────────────────────────────────────
class TestModoSaida:
    def test_modo_saida_bonus_perto_da_entrada(self, monkeypatch):
        """Show terminado há 30 min → modo_saida=True, bónus −1.5 min nos
        clusters a <150 m da ENTRADA, transição auditada."""
        from app.services import rota_leve, decision_log
        from app.services import fusao_rolante_demo as demo
        demo.demo_tick(T0)

        # baseline SEM modo saída
        base = rota_leve.compute_route("ENTRADA", "f", now_s=T0)
        assert base["modo_saida"] is False
        base_por_wc = {o["wc"]: o["total_min"] for o in base["opcoes"]}

        # show sintético terminado há 30 min (<90 min) — vê _pre_surto:
        # o import é from app.services.state import get_shows DENTRO da função
        monkeypatch.setattr("app.services.state.get_shows",
                            lambda: [_show_terminado(30 * 60.0)])
        rota_leve.reset()
        r = rota_leve.compute_route("ENTRADA", "f", now_s=T0)
        assert r["modo_saida"] is True

        # bónus aplicado às opções perto da ENTRADA (<150 m), clamp >= 0.1
        comparados = 0
        for o in r["opcoes"]:
            wc = o["wc"]
            cid = wc.split("_")[0].upper()
            if wc in base_por_wc and rota_leve._dist(cid, "ENTRADA") < 150.0:
                esperado = round(max(0.1, base_por_wc[wc] - 1.5), 1)
                assert o["total_min"] == pytest.approx(esperado, abs=0.11)
                comparados += 1
        assert comparados >= 1

        # transição False→True registada
        regs = decision_log.query(tipo="modo_saida")
        assert len(regs) >= 1
        assert regs[0]["depois"]["activo"] is True

    def test_modo_saida_falso_fora_da_janela(self, monkeypatch):
        """Show terminado há 2 h (>90 min) → modo_saida=False; e get_shows a
        rebentar → False (try/except)."""
        from app.services import rota_leve
        monkeypatch.setattr("app.services.state.get_shows",
                            lambda: [_show_terminado(120 * 60.0)])
        assert rota_leve._modo_saida(T0) is False

        def _explode():
            raise RuntimeError("sem shows")
        monkeypatch.setattr("app.services.state.get_shows", _explode)
        assert rota_leve._modo_saida(T0) is False


# ─────────────────────────────────────────────────────────────────────────────
# S20 — flag de congestão parado-vs-fluir
# ─────────────────────────────────────────────────────────────────────────────
class TestFlagCongestao:
    def test_dispara_com_multidao_parada_acima_75pct(self):
        """Ocupação ~83% da capacidade, parada ≥5 pontos → flag + auditoria."""
        from app.services import decision_log
        # WC-01_M cap=72 → 60/72 = 0.833; ocupação constante = fluxo parado
        for i in range(6):
            fr.ingest_cabecas("wc-01", "m", 60, fonte="prosegur",
                              ts_ms=T0_MS + i * 60_000, now_s=T0 + i * 60.0)
        p = fr.get_section_payload("wc-01_m", now_s=T0 + 6 * 60.0)
        assert p["flag_congestao"] is True
        regs = decision_log.query(tipo="congestao", seccao="wc-01_m")
        assert len(regs) == 1                       # transição logada UMA vez
        assert regs[0]["origem"] == "motor"

        # rota_leve penaliza +2 min a secção congestionada
        from app.services import rota_leve
        r = rota_leve.compute_route("WC-01", "m", now_s=T0 + 6 * 60.0)
        o = next((x for x in r["opcoes"] if x["wc"] == "wc-01_m"), None)
        if o is not None:
            assert o["congestao"] >= 2.0

    def test_nao_dispara_com_fila_a_fluir(self):
        """Ocupação alta MAS a variar (fluxo vivo) → flag False."""
        from app.services import decision_log
        # alterna 60/66 → |delta| médio = 6 ≥ 1.0 → fluxo a fluir
        for i in range(6):
            fr.ingest_cabecas("wc-01", "m", 60 if i % 2 == 0 else 66,
                              fonte="prosegur", ts_ms=T0_MS + i * 60_000,
                              now_s=T0 + i * 60.0)
        p = fr.get_section_payload("wc-01_m", now_s=T0 + 6 * 60.0)
        assert p["ocupacao"] / p["capacidade"] > 0.75   # cheio…
        assert p["flag_congestao"] is False             # …mas a fluir
        assert len(decision_log.query(tipo="congestao")) == 0
        # poucos pontos (<5) nunca dispara, mesmo parado
        fr.reset()
        fr.ingest_cabecas("wc-02", "m", 60, ts_ms=T0_MS, now_s=T0)
        p = fr.get_section_payload("wc-02_m", now_s=T0)
        assert p["flag_congestao"] is False


# ─────────────────────────────────────────────────────────────────────────────
# S11 — heartbeat dos 2 gateways
# ─────────────────────────────────────────────────────────────────────────────
class TestGatewaysHeartbeat:
    @pytest.mark.asyncio
    async def test_heartbeat_online_e_offline_auditado(self, client):
        """POST → online; calado 3 min → offline + alerta_crit auditado."""
        from app.services import decision_log
        r = await client.post("/api/v1/gateways/ug65-primario/heartbeat")
        assert r.status_code == 200
        assert r.json()["ok"] is True

        est = gateways_hb.estado()
        assert est["ug65-primario"]["online"] is True
        assert est["lg308n-reserva"]["online"] is False   # nunca falou

        # calado 3 min (>120 s) → transição para offline, auditada
        ts = est["ug65-primario"]["ultimo_hb_ts"]
        est2 = gateways_hb.estado(now_s=ts + 180.0)
        assert est2["ug65-primario"]["online"] is False
        regs = decision_log.query(tipo="alerta_crit", seccao="ug65-primario")
        assert len(regs) == 1
        assert "reserva assume" in regs[0]["justificacao"]
        # já offline: não duplica o alerta
        gateways_hb.estado(now_s=ts + 240.0)
        assert len(decision_log.query(tipo="alerta_crit",
                                      seccao="ug65-primario")) == 1

        # novo heartbeat → volta a online
        gateways_hb.heartbeat("ug65-primario", now_s=ts + 300.0)
        est3 = gateways_hb.estado(now_s=ts + 310.0)
        assert est3["ug65-primario"]["online"] is True

        r = await client.get("/api/v1/gateways")
        assert r.status_code == 200
        assert set(r.json()["gateways"].keys()) == {"ug65-primario",
                                                    "lg308n-reserva"}

    @pytest.mark.asyncio
    async def test_422s_ids_desconhecidos_e_combinacoes(self, client):
        """422 JSON em gateway desconhecido e combinações inválidas do PUT."""
        r = await client.post("/api/v1/gateways/gw-fantasma/heartbeat")
        assert r.status_code == 422
        assert "application/json" in r.headers["content-type"]

        casos = [
            # secção desconhecida
            ("wc-99_f", {"em_limpeza": True, "utilizador": "op"}),
            # em_limpeza num cluster M/F (não é secção)
            ("wc-04", {"em_limpeza": True, "utilizador": "op"}),
            # fechado numa secção (aplica-se a cluster)
            ("wc-04_f", {"fechado": True, "utilizador": "op"}),
            # os dois ao mesmo tempo
            ("wc-04", {"fechado": True, "em_limpeza": True,
                       "utilizador": "op"}),
            # nenhum dos dois
            ("wc-04", {"utilizador": "op"}),
        ]
        for sid, body in casos:
            r = await client.put(f"/api/v1/sections/{sid}/estado", json=body)
            assert r.status_code == 422, f"{sid} {body} → {r.status_code}"
            assert "application/json" in r.headers["content-type"]
        # unissexo: o cluster É a secção → em_limpeza válido em wc-05
        r = await client.put("/api/v1/sections/wc-05/estado", json={
            "em_limpeza": True, "eta_min": 8, "utilizador": "op",
        })
        assert r.status_code == 200

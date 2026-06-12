"""
Testa que /api/v1/flow e /api/v1/telemetry/clusters/now reportam os mesmos
valores de ocupacao_pct, fila e tempo_espera para cada cluster.

Executa com:  pytest app/test_flow_canonical.py -v
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from app.main import app
    return TestClient(app)


def test_flow_and_telemetry_same_occupancy(client: TestClient):
    """ocupacao_pct no /flow (por secção) deve vir da mesma fonte canónica
    que /telemetry/clusters/now (por cluster)."""
    r_flow = client.get("/api/v1/flow")
    r_tele = client.get("/api/v1/telemetry/clusters/now")

    assert r_flow.status_code == 200, f"/flow retornou {r_flow.status_code}"
    assert r_tele.status_code == 200, f"/telemetry retornou {r_tele.status_code}"

    flow_data = r_flow.json()
    tele_data = r_tele.json()

    # Indexar clusters do /telemetry por cluster_id
    tele_by_id: dict = {c["cluster_id"]: c["params"] for c in tele_data["clusters"]}

    # Agrupar secções do /flow por cluster e calcular média de ocupacao_pct
    from collections import defaultdict
    flow_occ_by_cluster: dict[str, list[float]] = defaultdict(list)
    flow_fila_by_cluster: dict[str, list[float]] = defaultdict(list)
    for sec in flow_data["secoes"]:
        cid = sec["cluster_id"]  # ex: "wc-01"
        flow_occ_by_cluster[cid].append(sec["ocupacao_pct"])
        flow_fila_by_cluster[cid].append(sec["fila_actual"])

    mismatches = []
    for cid, occs in flow_occ_by_cluster.items():
        t_params = tele_by_id.get(cid)
        if t_params is None:
            continue
        flow_avg = round(sum(occs) / len(occs), 1)
        # ocupacao_pct é o campo % do telemetry (ocupacao_instantanea = pessoas)
        tele_occ = float(t_params["ocupacao_pct"])
        # tolerância de 5 pp: flow_avg é média simples; ocupacao_pct é
        # ponderada pela capacidade das secções
        if abs(flow_avg - tele_occ) > 5.0:
            mismatches.append(
                f"{cid}: /flow avg={flow_avg:.1f}% vs /telemetry={tele_occ:.1f}%"
            )

    assert not mismatches, (
        "Divergência de ocupação entre /flow e /telemetry/clusters/now:\n"
        + "\n".join(mismatches)
    )


def test_flow_sections_have_canonical_fields(client: TestClient):
    """Cada secção do /flow deve ter ocupacao_pct, fila_actual e
    tempo_espera_min (garantia de que _enrich_with_canonical correu)."""
    r = client.get("/api/v1/flow")
    assert r.status_code == 200
    secoes = r.json().get("secoes", [])
    assert len(secoes) > 0, "Nenhuma secção retornada por /flow"
    for sec in secoes:
        assert "ocupacao_pct" in sec, f"ocupacao_pct em falta: {sec}"
        assert "fila_actual" in sec, f"fila_actual em falta: {sec}"
        assert "tempo_espera_min" in sec, f"tempo_espera_min em falta: {sec}"
        assert 0.0 <= sec["ocupacao_pct"] <= 100.0, (
            f"ocupacao_pct fora de [0,100]: {sec['ocupacao_pct']}"
        )


def test_telemetry_returns_all_clusters(client: TestClient):
    """Sanidade: /telemetry/clusters/now devolve os 8 clusters."""
    r = client.get("/api/v1/telemetry/clusters/now")
    assert r.status_code == 200
    data = r.json()
    assert data["cluster_count"] == 8
    ids = {c["cluster_id"] for c in data["clusters"]}
    expected = {f"wc-0{i}" for i in range(1, 9)}
    assert ids == expected, f"Clusters inesperados: {ids.symmetric_difference(expected)}"


# ─────────────────────────────────────────────────────────────────────────────
# Onda 12 Jun: ocupacao_pct E ocupacao_abs canónicos nas 14 secções
# ─────────────────────────────────────────────────────────────────────────────

def _section_cap(cluster_id: str, secao: str) -> int:
    """Capacidade oficial da secção (tabela única clusters_capacity)."""
    from app.clusters_capacity import capacity_gender, capacity_inside
    if secao == "U":
        return capacity_inside(cluster_id)
    return capacity_gender(cluster_id, secao)


def _clear_caches() -> None:
    """Força um snapshot novo — flow + telemetry leem o MESMO tick."""
    from app.services import state
    state._PAYLOAD_CACHE["data"] = None
    state._PAYLOAD_CACHE["derived"] = None


def test_flow_14_seccoes_abs_coerente_com_pct(client: TestClient):
    """a) Nas 14 secções, abs deriva do MESMO pct canónico:
    |100×ocupacao_abs/cap − ocupacao_pct| ≤ 2."""
    _clear_caches()
    r = client.get("/api/v1/flow")
    assert r.status_code == 200
    secoes = r.json()["secoes"]
    assert len(secoes) == 14, f"Esperadas 14 secções, vieram {len(secoes)}"
    erros = []
    for sec in secoes:
        cap = _section_cap(sec["cluster_id"], sec["secao"])
        assert cap > 0, f"capacidade inválida para {sec['cluster_id']}/{sec['secao']}"
        pct_de_abs = 100.0 * sec["ocupacao_abs"] / cap
        if abs(pct_de_abs - sec["ocupacao_pct"]) > 2.0:
            erros.append(
                f"{sec['cluster_id']}_{sec['secao']}: abs={sec['ocupacao_abs']} "
                f"(={pct_de_abs:.1f}%) vs pct={sec['ocupacao_pct']} (cap={cap})"
            )
    assert not erros, "abs incoerente com pct:\n" + "\n".join(erros)


def test_flow_soma_abs_igual_telemetry_exacto(client: TestClient):
    """a) SNAPSHOT ÚNICO — espelha o portao.sh do CEO, EXACTO (não ±1):
      - pessoas:  Σ ocupacao_abs == pessoas_estimadas
      - percent:  ocupacao_instantanea == round(100×Σabs/capacidade_total)
    Os dois endpoints consomem os MESMOS inteiros do snapshot do tick."""
    _clear_caches()

    r_flow = client.get("/api/v1/flow")
    r_tele = client.get("/api/v1/telemetry/clusters/now")
    assert r_flow.status_code == 200 and r_tele.status_code == 200

    tele_by_id = {c["cluster_id"]: c["params"] for c in r_tele.json()["clusters"]}
    from collections import defaultdict
    soma_abs: dict[str, int] = defaultdict(int)
    for sec in r_flow.json()["secoes"]:
        soma_abs[sec["cluster_id"]] += int(sec["ocupacao_abs"])

    erros = []
    for cid, total in sorted(soma_abs.items()):
        p = tele_by_id[cid]
        if total != int(p["pessoas_estimadas"]):
            erros.append(f"{cid}: Σabs={total} != pessoas_estimadas={p['pessoas_estimadas']}")
        cap_total = int(p["capacidade_total"])
        # a MESMA expressão do portao.sh: round(100*S[cid]/capacidade_total)
        if int(p["ocupacao_instantanea"]) != round(100 * total / cap_total):
            erros.append(
                f"{cid}: ocupacao_instantanea={p['ocupacao_instantanea']} "
                f"!= round(100×{total}/{cap_total})={round(100 * total / cap_total)}"
            )
        pct_esperado = round(min(100.0, 100.0 * total / cap_total), 1)
        if float(p["ocupacao_pct"]) != pct_esperado:
            erros.append(f"{cid}: ocupacao_pct={p['ocupacao_pct']} != {pct_esperado}")
    assert not erros, "Divergência flow/telemetry no mesmo tick:\n" + "\n".join(erros)


def test_snapshot_ts_identico_em_todos_os_endpoints(client: TestClient):
    """SNAPSHOT PARTILHADO (critério nº1): /flow, /telemetry, /state, /kpis,
    /tv e /sections devolvem o MESMO snapshot_ts dentro do mesmo tick —
    prova de que todos leem o mesmo objecto."""
    _clear_caches()
    ts_flow = client.get("/api/v1/flow").json()["snapshot_ts"]
    ts_tele = client.get("/api/v1/telemetry/clusters/now").json()["snapshot_ts"]
    ts_state = client.get("/api/v1/state").json()["snapshot_ts"]
    ts_kpis = client.get("/api/v1/kpis").json()["snapshot_ts"]
    ts_tv = client.get("/api/v1/tv/screen-01").json()["snapshot_ts"]
    ts_secs = client.get("/api/v1/sections").json()["snapshot_ts"]
    vistos = {"flow": ts_flow, "telemetry": ts_tele, "state": ts_state,
              "kpis": ts_kpis, "tv": ts_tv, "sections": ts_secs}
    assert ts_flow and len(set(vistos.values())) == 1, (
        f"snapshot_ts diverge entre endpoints: {vistos}"
    )
    # e o ts de cada cluster do telemetry é o mesmo carimbo
    r = client.get("/api/v1/telemetry/clusters/now").json()
    assert all(c["ts"] == r["snapshot_ts"] for c in r["clusters"]), (
        "ts por cluster difere do snapshot_ts"
    )


def test_ocupacao_nunca_deriva_de_pessoas_estimadas(client: TestClient):
    """b) Caso sintético: âncora canónica de 60 pessoas em wc-06 ENQUANTO o
    ingest recebe pessoas_estimadas=100 (WiFi, dentro+perto). O /flow tem de
    somar 60 (fusão canónica), NUNCA 100 (input WiFi)."""
    from app.services import fusao_rolante, ingest_store
    import time as _t
    try:
        # input WiFi a "gritar" 100 — entra na fusão como fonte, nada mais
        ingest_store.put("wc-06", {"pessoas_estimadas": 100},
                         int(_t.time() * 1000))
        # âncora canónica: 60 cabeças dentro (secção única U, sem género)
        fusao_rolante.ingest_cabecas("wc-06", None, 60.0, fonte="manual")
        _clear_caches()
        r_flow = client.get("/api/v1/flow")
        r_tele = client.get("/api/v1/telemetry/clusters/now")
        soma = sum(int(s["ocupacao_abs"]) for s in r_flow.json()["secoes"]
                   if s["cluster_id"] == "wc-06")
        assert soma == 60, f"/flow wc-06 soma {soma} (esperado 60, nunca 100)"
        tele = next(c["params"] for c in r_tele.json()["clusters"]
                    if c["cluster_id"] == "wc-06")
        assert int(tele["pessoas_estimadas"]) == 60, (
            f"telemetry wc-06 pessoas_estimadas={tele['pessoas_estimadas']} "
            "(esperado 60 — pessoas_estimadas WiFi é input de fusão, nunca output)"
        )
        # % exacto do portão: round(100×60/208) = 29, nunca round(100×100/208)=48
        assert int(tele["ocupacao_instantanea"]) == round(100 * 60 / 208), (
            f"telemetry wc-06 occ%={tele['ocupacao_instantanea']} (esperado 29)"
        )
    finally:
        fusao_rolante.reset()
        ingest_store._STORE.pop("wc-06", None)
        _clear_caches()


def test_dois_curls_no_mesmo_tick_sao_identicos(client: TestClient):
    """SNAPSHOT ÚNICO por construção: duas leituras do /telemetry dentro do
    mesmo tick devolvem payloads byte-a-byte idênticos (incluindo ts)."""
    _clear_caches()
    r1 = client.get("/api/v1/telemetry/clusters/now")
    r2 = client.get("/api/v1/telemetry/clusters/now")
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json() == r2.json(), "dois curls no mesmo tick divergem — snapshot não é único"


def test_unissexo_sem_campos_de_genero_no_telemetry(client: TestClient):
    """REGRA DURA: wc-05/wc-06 (unissexo) NUNCA levam homens/mulheres no
    payload do telemetry — nem como null; o campo não existe.
    Os clusters M/F continuam a tê-los."""
    _clear_caches()
    r = client.get("/api/v1/telemetry/clusters/now")
    assert r.status_code == 200
    for c in r.json()["clusters"]:
        params = c["params"]
        if c["cluster_id"] in ("wc-05", "wc-06"):
            assert "homens" not in params, f"{c['cluster_id']}: campo 'homens' presente"
            assert "mulheres" not in params, f"{c['cluster_id']}: campo 'mulheres' presente"
        else:
            assert "homens" in params and "mulheres" in params, (
                f"{c['cluster_id']}: M/F sem homens/mulheres"
            )


def test_unissexo_nunca_pct_100_com_canonico_abaixo_da_cap(client: TestClient):
    """c) WC-05/WC-06 (unissexo, secção única, SEM género): com o canónico
    bem abaixo da capacidade (133/208), o /flow nunca pode reportar pct=100.
    Regressão do falso 100% que excluía a válvula de pressão WC-06 do routing."""
    from app.services import fusao_rolante
    try:
        # âncoras de cabeças muito abaixo da cap — sem chave de género
        fusao_rolante.ingest_cabecas("wc-05", None, 25.0, fonte="manual")
        fusao_rolante.ingest_cabecas("wc-06", None, 40.0, fonte="manual")
        _clear_caches()
        r = client.get("/api/v1/flow")
        assert r.status_code == 200
        uni = {s["cluster_id"]: s for s in r.json()["secoes"] if s["secao"] == "U"}
        assert set(uni) == {"wc-05", "wc-06"}, f"secções U inesperadas: {set(uni)}"
        for cid, cap in (("wc-05", 133), ("wc-06", 208)):
            sec = uni[cid]
            assert sec["ocupacao_pct"] < 100.0, (
                f"{cid}: pct={sec['ocupacao_pct']} com canónico ≪ cap={cap} "
                "— falso 100% (bug de denominador)"
            )
            assert sec["ocupacao_abs"] < cap, (
                f"{cid}: abs={sec['ocupacao_abs']} ≥ cap={cap}"
            )
            # coerência directa com a âncora ingerida (±2 pessoas de arredondamento)
            esperado = {"wc-05": 25, "wc-06": 40}[cid]
            assert abs(sec["ocupacao_abs"] - esperado) <= 2, (
                f"{cid}: abs={sec['ocupacao_abs']} vs âncora={esperado}"
            )
    finally:
        fusao_rolante.reset()
        _clear_caches()


def test_unissexo_restore_clampa_ocupacao_a_capacidade():
    """c2) Snapshot (versão actual) com ocupacao > capacidade não pode
    produzir ocup/cap > 1 (a causa do falso pct=100 após restore)."""
    from app.services import fusao_rolante
    try:
        est = fusao_rolante.get_estimador("wc-06")
        assert est is not None and est.capacidade == 208
        est.restore({"versao": fusao_rolante.SNAPSHOT_VERSAO,
                     "ocupacao": 999.0, "tem_dados": True})
        assert est.ocupacao is not None and est.ocupacao <= 208.0, (
            f"restore não clampou: ocupacao={est.ocupacao} > cap=208"
        )
    finally:
        fusao_rolante.reset()


def test_restore_rejeita_snapshot_de_versao_antiga():
    """c3) Snapshot com versão antiga (ou sem versão — pré-deploy) é
    REJEITADO: a secção arranca limpa, sem reancorar o motor com estado
    de um deploy anterior."""
    from app.services import fusao_rolante
    try:
        for snap_antigo in ({"ocupacao": 150.0, "tem_dados": True},          # sem versao
                            {"versao": 1, "ocupacao": 150.0, "tem_dados": True},
                            {"versao": "lixo", "ocupacao": 150.0, "tem_dados": True}):
            fusao_rolante.reset()
            est = fusao_rolante.get_estimador("wc-06")
            assert est is not None
            est.restore(snap_antigo)
            assert est.ocupacao is None, f"snapshot antigo aplicado: {snap_antigo}"
            assert est.tem_dados is False, f"tem_dados ficou True com {snap_antigo}"
        # sanidade: a versão ACTUAL é aceite (round-trip to_dict → restore)
        fusao_rolante.reset()
        est = fusao_rolante.get_estimador("wc-06")
        est.ocupacao = 42.0
        est.tem_dados = True
        snap = est.to_dict()
        assert snap["versao"] == fusao_rolante.SNAPSHOT_VERSAO
        fusao_rolante.reset()
        est2 = fusao_rolante.get_estimador("wc-06")
        est2.restore(snap)
        assert est2.tem_dados is True and est2.ocupacao == 42.0
    finally:
        fusao_rolante.reset()


def test_ocupacao_instantanea_arredondamento_unico():
    """Regressão (apanhado em produção): 100×85/126 = 67.46 tem de dar 67.
    Com paragem intermédia a 1 casa decimal dava 67.5 → 68 (dupla
    arredondagem) e divergia 1pp da relação round(100×Σabs/cap)."""
    from app.services.cluster_telemetry import build_cluster_payload
    state = {"sections": [
        {"section_id": "WC-02_M", "gender": "M", "ocupacao_pct": 50.0,
         "ocupacao_abs": 40, "fila_atual": 0, "tempo_espera_min": 0.0,
         "fluxo_entrada_pmin": 0.0, "status": "normal", "simulated": True},
        {"section_id": "WC-02_F", "gender": "F", "ocupacao_pct": 60.0,
         "ocupacao_abs": 45, "fila_atual": 0, "tempo_espera_min": 0.0,
         "fluxo_entrada_pmin": 0.0, "status": "normal", "simulated": True},
    ]}
    wc02 = next(c for c in build_cluster_payload(state)
                if c["cluster_id"] == "wc-02")
    p = wc02["params"]
    assert p["pessoas_estimadas"] == 85
    # 100×85/126 = 67.46 → arredondamento ÚNICO = 67 (nunca 68)
    assert p["ocupacao_instantanea"] == 67, (
        f"dupla arredondagem: occ={p['ocupacao_instantanea']} (esperado 67)"
    )
    assert p["ocupacao_pct"] == 67.5  # % a 1dp para o frontend (mesmos abs)


def test_health_devolve_git_sha(client: TestClient):
    """Bónus: /health devolve git_sha (RAILWAY_GIT_COMMIT_SHA ou 'dev')."""
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    sha = r.json().get("git_sha")
    assert isinstance(sha, str) and 1 <= len(sha) <= 7, f"git_sha inválido: {sha!r}"


def test_flow_fila_e_espera_continuam_canonicos(client: TestClient):
    """d) Regressão: fila_actual e tempo_espera_min do /flow continuam
    idênticos ao /telemetry/clusters/now (Σ fila por cluster; max espera)."""
    _clear_caches()
    r_flow = client.get("/api/v1/flow")
    r_tele = client.get("/api/v1/telemetry/clusters/now")
    assert r_flow.status_code == 200 and r_tele.status_code == 200

    tele_by_id = {c["cluster_id"]: c["params"] for c in r_tele.json()["clusters"]}
    from collections import defaultdict
    fila: dict[str, int] = defaultdict(int)
    espera: dict[str, float] = defaultdict(float)
    for sec in r_flow.json()["secoes"]:
        cid = sec["cluster_id"]
        fila[cid] += int(sec["fila_actual"])
        espera[cid] = max(espera[cid], float(sec["tempo_espera_min"]))

    erros = []
    for cid in sorted(fila):
        t = tele_by_id[cid]
        if fila[cid] != int(t["fila_atual"]):
            erros.append(f"{cid}: fila /flow={fila[cid]} vs telemetry={t['fila_atual']}")
        if abs(espera[cid] - float(t["tempo_espera_min"])) > 0.05:
            erros.append(
                f"{cid}: espera /flow={espera[cid]} vs telemetry={t['tempo_espera_min']}"
            )
    assert not erros, "fila/espera divergem do telemetry:\n" + "\n".join(erros)

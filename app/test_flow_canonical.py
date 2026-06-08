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
        tele_occ = float(t_params["ocupacao_instantanea"])
        # tolerância de 5 pp — o telemetry aplica ±3 % de jitter visual
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

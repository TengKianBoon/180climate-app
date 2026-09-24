"""Machine-discovery and consequential-action guards for authorised AI agents."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app, raise_server_exceptions=True)
ROOT = Path(__file__).parents[1]


def _catalogue() -> dict:
    response = client.get("/.well-known/180climate-services.json")
    assert response.status_code == 200
    return response.json()


def test_well_known_catalogue_is_canonical_and_has_all_services() -> None:
    catalogue = _catalogue()
    assert catalogue["$schema"] == "/schemas/agent-service-catalogue-v1.json"
    assert catalogue["discovery"]["canonical_url"] == "/.well-known/180climate-services.json"
    assert catalogue["discovery"]["openapi_url"] == "/openapi.json"
    assert catalogue["discovery"]["commercial_catalogue_url"] == "/.well-known/180climate-commercial.json"
    assert {item["service_id"] for item in catalogue["services"]} == {
        "carbon.pre_fs.v1",
        "eudr.plot_screen.v1",
        "fieldwork.match_intro.v1",
    }
    assert catalogue == client.get("/services.json").json()


def test_catalogue_references_public_versioned_schemas() -> None:
    catalogue = _catalogue()
    schema_urls = {catalogue["$schema"]}
    for service in catalogue["services"]:
        schema_urls.add(service["input_schema_url"])
        schema_urls.add(service["output_schema_url"])
        if "provider_input_schema_url" in service:
            schema_urls.add(service["provider_input_schema_url"])
        for action in service["agent_procurement"]["actions"]:
            schema_urls.update(
                url
                for key in ("input_schema_url", "output_schema_url")
                if (url := action.get(key))
            )
    for url in schema_urls:
        response = client.get(url)
        assert response.status_code == 200, url
        assert response.headers["content-type"].startswith("application/schema+json")
        json.loads(response.content)


def test_openapi_operation_ids_are_unique_and_catalogue_actions_resolve() -> None:
    openapi = client.get("/openapi.json").json()
    operations = [
        operation
        for path_item in openapi["paths"].values()
        for method, operation in path_item.items()
        if method.lower() in {"get", "post", "put", "patch", "delete"}
    ]
    operation_ids = [operation["operationId"] for operation in operations]
    assert len(operation_ids) == len(set(operation_ids))

    catalogue_ids = {
        action["operation_id"]
        for service in _catalogue()["services"]
        for action in service["agent_procurement"]["actions"]
        if action["transport"] == "openapi"
    }
    assert catalogue_ids <= set(operation_ids)
    by_id = {operation["operationId"]: operation for operation in operations}
    for operation_id in catalogue_ids:
        annotations = by_id[operation_id]["x-agent-tool-annotations"]
        assert set(annotations) == {
            "readOnlyHint",
            "destructiveHint",
            "idempotentHint",
            "openWorldHint",
        }

    assert by_id["submitCarbonLead"]["x-agent-tool-annotations"]["openWorldHint"] is True
    assert by_id["createAndDeliverCarbonReport"]["x-agent-tool-annotations"]["idempotentHint"] is False


def test_consequential_actions_and_current_side_effects_are_explicit() -> None:
    catalogue = _catalogue()
    policy = catalogue["agent_policy"]
    assert policy["authorised_agent_only"] is True
    assert policy["annotations_are_hints"] is True
    assert any("contract" in item.lower() for item in policy["never_autonomous"])
    assert any("payment" in item.lower() for item in policy["never_autonomous"])

    services = {item["service_id"]: item for item in catalogue["services"]}
    eudr_action = services["eudr.plot_screen.v1"]["agent_procurement"]["actions"][0]
    assert eudr_action["requires_immediate_user_approval"] is True
    assert "emails_180climate" in eudr_action["side_effects"]
    assert eudr_action["annotations"]["readOnlyHint"] is False
    assert eudr_action["annotations"]["idempotentHint"] is False

    fieldwork = services["fieldwork.match_intro.v1"]["agent_procurement"]
    assert fieldwork["readiness"] == "human_handoff_live_machine_intake_staged"
    staged = [
        action
        for action in fieldwork["actions"]
        if action["action_id"].startswith("register_native_")
    ]
    assert staged
    assert all(action["availability"] == "fail_closed_until_launch_controls_pass" for action in staged)
    assert all(action["annotations"]["idempotentHint"] is True for action in staged)


def test_agent_catalogue_schema_is_committed_and_parseable() -> None:
    schema_path = ROOT / "frontend" / "schemas" / "agent-service-catalogue-v1.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "/schemas/agent-service-catalogue-v1.json"

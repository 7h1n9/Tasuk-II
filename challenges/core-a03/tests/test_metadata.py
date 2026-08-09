from pathlib import Path

import yaml


def test_metadata_public_boundary():
    metadata = yaml.safe_load((Path(__file__).parents[1] / "metadata.yaml").read_text(encoding="utf-8"))
    assert metadata["id"] == "core-a03"
    assert set(metadata) == {"id", "version", "public", "internal"}
    assert metadata["internal"]["vulnerability_class"] == "client_controlled_role_context"
    assert "admin=true" not in str(metadata["public"]).lower()
    assert not ({"expected_chain", "solver", "flag_location", "secret", "payload", "ground_truth"} & set(metadata["public"]))

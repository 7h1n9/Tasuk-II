from pathlib import Path

import yaml


def test_metadata_public_boundary():
    metadata = yaml.safe_load((Path(__file__).parents[1] / "metadata.yaml").read_text(encoding="utf-8"))
    assert metadata["id"] == "core-a05"
    assert set(metadata) == {"id", "version", "public", "internal"}
    assert metadata["internal"]["vulnerability_class"] == "workflow_authorization_bypass"
    assert "approved=1" not in str(metadata["public"])
    assert not ({"expected_chain", "solver", "flag_location", "secret", "payload", "ground_truth"} & set(metadata["public"]))

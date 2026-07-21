from pathlib import Path

import yaml


def test_metadata_identity_and_public_boundary():
    path = Path(__file__).parents[1] / "metadata.yaml"
    metadata = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert metadata["id"] == "core-a01"
    assert metadata["public"]["name"] == "设备报修工单平台"
    assert metadata["internal"]["vulnerability_class"] == "broken_object_level_authorization"
    assert "flag_value" not in metadata["public"]

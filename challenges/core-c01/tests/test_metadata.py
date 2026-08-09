from pathlib import Path
import yaml


def test_metadata_public_boundary():
    metadata = yaml.safe_load((Path(__file__).parents[1] / "metadata.yaml").read_text(encoding="utf-8"))
    assert metadata["id"] == "core-c01"
    assert metadata["public"]["name"] == "历史文档预览中心"
    assert metadata["internal"]["vulnerability_class"] == "double_decoding_path_normalization"
    assert set(metadata["public"]["tags"]).isdisjoint({"path-traversal", "directory-traversal"})

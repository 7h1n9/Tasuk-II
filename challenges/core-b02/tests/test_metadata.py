from pathlib import Path
import yaml


def test_metadata_public_boundary():
    metadata = yaml.safe_load((Path(__file__).parents[1] / "metadata.yaml").read_text(encoding="utf-8"))
    assert metadata["id"] == "core-b02"
    assert metadata["public"]["name"] == "资产保修核验平台"
    assert metadata["internal"]["vulnerability_class"] == "boolean_based_query_inference"
    assert set(metadata["public"]["tags"]).isdisjoint({"sqli", "sql-injection", "blind-injection"})
    home = (Path(__file__).parents[1] / "app" / "app.py").read_text(encoding="utf-8").split("def index", 1)[1].split("def help_page", 1)[0]
    assert "service_settings" not in home

import re
import requests


def test_archive_reference_remains_stable_on_normal_reset(base_url, reset_instance):
    def reference():
        page = requests.get(base_url + "/documents/migration-record").text
        href = re.search(r"href=['\"]([^'\"]*/preview\?[^'\"]+)['\"]", page).group(1)
        content = requests.get(base_url + href).text
        return re.search(r"legacy_archive_ref:\s*(private/[A-Za-z0-9._-]+\.txt)", content).group(1)
    before = reference()
    reset_instance()
    assert reference() == before

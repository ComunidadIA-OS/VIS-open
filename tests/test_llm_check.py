from decision.llm_check import list_models


def test_list_models_sorted_ids_and_sends_key_as_bearer_without_returning_it():
    seen = {}

    def fake_get(url, headers):
        seen.update(url=url, headers=dict(headers))
        return {"data": [{"id": "qwen-b"}, {"id": "qwen-a"}, {"object": "x"}]}

    assert list_models("http://x/v1/", "SECRETO", fake_get) == ["qwen-a", "qwen-b"]
    assert seen["url"] == "http://x/v1/models" and seen["headers"] == {
        "Authorization": "Bearer SECRETO"
    }


def test_list_models_without_key_sends_no_auth_header():
    seen = {}
    list_models("http://x/v1", "", lambda u, h: seen.update(h=dict(h)) or {"data": []})
    assert seen["h"] == {}

from dashboard.avatar import avatar_html


def test_text_cannot_break_out_of_script():
    html = avatar_html("hola </script><img src=x onerror=alert(1)>", "sec-hitl", True)
    body = html.split("<script>")[-1]
    assert "</script><img" not in body and body.count("</script>") == 1
    assert "const t=" in body and "speak=true" in body


def test_idle_does_not_speak():
    assert "speak=false" in avatar_html(None)

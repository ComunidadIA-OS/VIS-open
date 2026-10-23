import urllib.error
import urllib.request

import pytest

from dashboard.videoserver import _byte_range, video_url


def test_serves_byte_ranges_without_reading_the_whole_file(tmp_path):
    video = tmp_path / "V9.mp4"
    video.write_bytes(bytes(range(100)))
    url = video_url(video)
    assert url.startswith("http://127.0.0.1:") and url.endswith("/V9.mp4")
    req = urllib.request.Request(url, headers={"Range": "bytes=10-19"})
    with urllib.request.urlopen(req) as r:
        assert r.status == 206 and r.read() == bytes(range(10, 20))
        assert r.headers["Content-Range"] == "bytes 10-19/100"
    with urllib.request.urlopen(url) as r:
        assert r.status == 200 and len(r.read()) == 100


def test_only_mp4_of_that_folder(tmp_path):
    (tmp_path / "V9.mp4").write_bytes(b"x")
    (tmp_path / "secreto.txt").write_text("no")
    base = video_url(tmp_path / "V9.mp4").rsplit("/", 1)[0]
    for name in ("secreto.txt", "..%2Fsecreto.txt", "nada.mp4"):
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(f"{base}/{name}")
        assert err.value.code == 404


def test_byte_range_parsing():
    assert _byte_range("bytes=0-", 50) == (0, 49)
    assert _byte_range("bytes=-10", 50) == (40, 49)
    assert _byte_range("bytes=5-500", 50) == (5, 49)
    assert _byte_range(None, 50) is None and _byte_range("items=1-2", 50) is None

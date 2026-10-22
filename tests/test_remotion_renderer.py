import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.remotion_renderer import RemotionRenderer


def test_remotion_renderer_is_available(tmp_path):
    renderer = RemotionRenderer(remotion_dir=tmp_path)
    assert renderer.is_available() is False

    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    with patch("shutil.which", return_value="C:\\Program Files\\nodejs\\npx.cmd"):
        assert renderer.is_available() is True


def test_remotion_sync_video_to_public(tmp_path):
    remotion_dir = tmp_path / "remotion"
    remotion_dir.mkdir()
    (remotion_dir / "package.json").write_text("{}", encoding="utf-8")

    src_video = tmp_path / "sample.mp4"
    src_video.write_bytes(b"dummy_video_bytes")

    renderer = RemotionRenderer(remotion_dir=remotion_dir)
    target_name = renderer.sync_video_to_public(src_video, "my-test.mp4")

    assert target_name == "my-test.mp4"
    dest = remotion_dir / "public" / "my-test.mp4"
    assert dest.exists()
    assert dest.read_bytes() == b"dummy_video_bytes"


def test_remotion_sync_video_missing_file(tmp_path):
    renderer = RemotionRenderer(remotion_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        renderer.sync_video_to_public(tmp_path / "non_existent.mp4")


@patch("subprocess.run")
def test_remotion_render_composition_success(mock_subproc, tmp_path):
    remotion_dir = tmp_path / "remotion"
    remotion_dir.mkdir()
    (remotion_dir / "package.json").write_text("{}", encoding="utf-8")

    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_subproc.return_value = mock_res

    with patch("shutil.which", return_value="npx"):
        renderer = RemotionRenderer(remotion_dir=remotion_dir)
        output_file = tmp_path / "final.mp4"
        props = {"hookTitle": "Test Title", "discountPrice": "Rp 50.000"}

        result = renderer.render_composition(
            composition_id="VeloraUGC",
            output_path=output_file,
            props=props,
            port=3035,
        )

        assert result == output_file
        mock_subproc.assert_called_once()
        args, kwargs = mock_subproc.call_args
        cmd = args[0]
        assert "npx" in cmd
        assert "VeloraUGC" in cmd
        assert "--port=3035" in cmd

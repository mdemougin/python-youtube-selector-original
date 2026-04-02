"""Tests for youtube_auth."""

import pickle
from unittest.mock import MagicMock, patch

import pytest

import youtube_auth
from tests.pickleable_creds import PickleableCreds


@pytest.fixture
def mock_root():
    return MagicMock()


def test_build_youtube_service_valid_pickle(mock_root, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    creds = PickleableCreds(valid=True)
    with open("token.pickle", "wb") as f:
        pickle.dump(creds, f)

    fake_service = object()
    with patch("youtube_auth.build", return_value=fake_service) as b:
        out = youtube_auth.build_youtube_service(mock_root)

    assert out is fake_service
    b.assert_called_once()
    assert b.call_args.kwargs["credentials"].valid is True


def test_build_youtube_service_refresh_success(mock_root, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    creds = PickleableCreds(valid=False, expired=True, refresh_token="rt")
    with open("token.pickle", "wb") as f:
        pickle.dump(creds, f)

    fake_service = object()
    with patch("youtube_auth.build", return_value=fake_service):
        out = youtube_auth.build_youtube_service(mock_root)

    assert out is fake_service
    with open("token.pickle", "rb") as f:
        reloaded = pickle.load(f)
    assert isinstance(reloaded, PickleableCreds)
    assert reloaded.valid is True


def test_build_youtube_service_refresh_error_then_reauth(mock_root, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    old = PickleableCreds(
        valid=False, expired=True, refresh_token="rt", fail_refresh=True
    )
    with open("token.pickle", "wb") as f:
        pickle.dump(old, f)

    (tmp_path / "client_secrets.json").write_text("{}")
    new_creds = PickleableCreds(valid=True)
    flow_mock = MagicMock()
    flow_mock.run_local_server.return_value = new_creds
    fake_service = object()

    with patch("youtube_auth.build", return_value=fake_service), patch(
        "youtube_auth.InstalledAppFlow.from_client_secrets_file",
        return_value=flow_mock,
    ):
        out = youtube_auth.build_youtube_service(mock_root)

    assert out is fake_service
    flow_mock.run_local_server.assert_called_once()
    with open("token.pickle", "rb") as f:
        saved = pickle.load(f)
    assert isinstance(saved, PickleableCreds)
    assert saved.valid is True


def test_build_youtube_service_refresh_error_remove_raises_oserror(
    mock_root, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    old = PickleableCreds(
        valid=False, expired=True, refresh_token="rt", fail_refresh=True
    )
    with open("token.pickle", "wb") as f:
        pickle.dump(old, f)

    (tmp_path / "client_secrets.json").write_text("{}")
    new_creds = PickleableCreds(valid=True)
    flow_mock = MagicMock()
    flow_mock.run_local_server.return_value = new_creds
    fake_service = object()
    real_remove = youtube_auth.os.remove

    def remove_side_effect(path, *a, **kw):
        s = str(path)
        if s.endswith("token.pickle"):
            raise OSError("simulated fs error")
        return real_remove(path)

    with patch("youtube_auth.build", return_value=fake_service), patch(
        "youtube_auth.InstalledAppFlow.from_client_secrets_file",
        return_value=flow_mock,
    ), patch("youtube_auth.os.remove", side_effect=remove_side_effect):
        out = youtube_auth.build_youtube_service(mock_root)

    assert out is fake_service
    flow_mock.run_local_server.assert_called_once()


def test_run_installed_flow_missing_secrets(mock_root, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("youtube_auth.messagebox.showinfo") as mb:
        out = youtube_auth._run_installed_flow(mock_root)
    assert out is None
    mb.assert_called_once()
    mock_root.quit.assert_called_once()


def test_run_installed_flow_success(mock_root, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "client_secrets.json").write_text("{}")
    creds = PickleableCreds(valid=True)
    flow = MagicMock()
    flow.run_local_server.return_value = creds
    with patch(
        "youtube_auth.InstalledAppFlow.from_client_secrets_file",
        return_value=flow,
    ):
        out = youtube_auth._run_installed_flow(mock_root)
    assert out is creds


def test_build_youtube_service_flow_returns_none(mock_root, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("youtube_auth._run_installed_flow", return_value=None):
        assert youtube_auth.build_youtube_service(mock_root) is None


def test_build_youtube_service_no_pickle_runs_flow(mock_root, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "client_secrets.json").write_text("{}")
    flow_creds = PickleableCreds(valid=True)
    flow_mock = MagicMock()
    flow_mock.run_local_server.return_value = flow_creds
    fake_service = object()

    with patch("youtube_auth.build", return_value=fake_service), patch(
        "youtube_auth.InstalledAppFlow.from_client_secrets_file",
        return_value=flow_mock,
    ):
        out = youtube_auth.build_youtube_service(mock_root)

    assert out is fake_service
    with open("token.pickle", "rb") as f:
        saved = pickle.load(f)
    assert isinstance(saved, PickleableCreds)
    assert saved.valid is True


def test_build_youtube_service_invalid_pickle_creds_no_refresh_token(
    mock_root, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    creds = PickleableCreds(valid=False, expired=True, refresh_token=None)
    with open("token.pickle", "wb") as f:
        pickle.dump(creds, f)

    (tmp_path / "client_secrets.json").write_text("{}")
    flow_creds = PickleableCreds(valid=True)
    flow_mock = MagicMock()
    flow_mock.run_local_server.return_value = flow_creds

    with patch("youtube_auth.build", return_value=object()), patch(
        "youtube_auth.InstalledAppFlow.from_client_secrets_file",
        return_value=flow_mock,
    ):
        youtube_auth.build_youtube_service(mock_root)

    flow_mock.run_local_server.assert_called_once()

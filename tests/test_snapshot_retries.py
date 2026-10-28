import json
from pathlib import Path
import pytest
from kars.storage import atomic_json


def test_longer_windows_lock_eventually_replaces_complete_snapshot(tmp_path,monkeypatch):
    target=tmp_path/'live.json'
    target.write_text('{"time":0}')
    original=Path.replace
    calls=[]
    def locked(path,destination):
        calls.append(path)
        if len(calls)<=25:raise PermissionError('Windows sharing violation')
        return original(path,destination)
    monkeypatch.setattr(Path,'replace',locked)
    monkeypatch.setattr('kars.storage.time.sleep',lambda _:None)
    atomic_json(target,{'time':42})
    assert len(calls)==26
    assert json.loads(target.read_text())=={'time':42}
    assert not list(tmp_path.glob('*.tmp'))


def test_persistent_write_error_is_reported_and_previous_snapshot_survives(tmp_path,monkeypatch):
    target=tmp_path/'live.json';target.write_text('{"time":0}')
    def locked(*_):raise PermissionError('Persistent lock')
    monkeypatch.setattr(Path,'replace',locked)
    monkeypatch.setattr('kars.storage.time.sleep',lambda _:None)
    with pytest.raises(PermissionError,match='Persistent lock'):
        atomic_json(target,{'time':42})
    assert json.loads(target.read_text())=={'time':0}
    assert not list(tmp_path.glob('*.tmp'))

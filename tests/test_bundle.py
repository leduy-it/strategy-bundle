import json
import shutil
import uuid
import pytest
import httpx
from promete_strategy_bundle.contract import Bundle, verify_bundle, fingerprint
from promete_strategy_bundle.cli import api_url, import_bundle, main
from promete_strategy_bundle.store import BundleStore, BusyError


def test_valid_bundle_and_move(bundle_dir, tmp_path_factory):
    bundle=verify_bundle(bundle_dir)
    moved=tmp_path_factory.mktemp('moved')/'bundle';shutil.copytree(bundle_dir,moved)
    assert fingerprint(verify_bundle(moved)) == fingerprint(bundle)

@pytest.mark.parametrize('mutate',[
    lambda d:d['artifacts'][0].update(path='../model.zip'),
    lambda d:d['artifacts'][0].update(path='/etc/passwd'),
    lambda d:d['artifacts'][0].update(path='x\\model.zip'),
    lambda d:d['artifacts'][0].update(size=True),
    lambda d:d['evaluation']['metrics'].update(totalReturn=10),
    lambda d:d['evaluation']['metrics'].update(maxDrawdown=.1),
    lambda d:d['evaluation']['metrics'].update(nullReasons={}),
    lambda d:d['model'].update(features=['close','close']),
    lambda d:d['model'].update(normalization='obs_rms'),
    lambda d:d['evaluation']['nav'][0].update(balance=float('nan')),
    lambda d:d['evaluation']['nav'].reverse(),
    lambda d:d['strategy']['config'].update(stocks=['SSI']),
])
def test_invalid_contract(bundle_dir, mutate):
    data=json.loads((bundle_dir/'manifest.json').read_text());mutate(data)
    with pytest.raises(ValueError):Bundle.model_validate(data)


def test_checksum_and_lfs_pointer(bundle_dir):
    (bundle_dir/'model.zip').write_text('version https://git-lfs.github.com/spec/v1')
    with pytest.raises(ValueError,match='checksum/size'):verify_bundle(bundle_dir)


def test_symlink_rejected(bundle_dir):
    model=bundle_dir/'model.zip'; model.rename(bundle_dir/'actual.zip');model.symlink_to('actual.zip')
    with pytest.raises(ValueError,match='symlinks'):verify_bundle(bundle_dir)


def test_renamed_paths_same_identity(bundle_dir):
    bundle=verify_bundle(bundle_dir); data=bundle.model_dump(mode='json')
    data['artifacts'][0]['path']='moved/model.zip'
    assert fingerprint(bundle)==fingerprint(Bundle.model_validate(data))


def test_store_sealing_and_lock(bundle_dir,tmp_path_factory):
    store=BundleStore(tmp_path_factory.mktemp('stage')); key=str(uuid.uuid4()); bundle=verify_bundle(bundle_dir)
    store.initialize(key,bundle.model_dump(mode='json'))
    for artifact in bundle.artifacts:shutil.copyfile(bundle_dir/artifact.path,store.directory(key)/artifact.id)
    with store.locked(key):
        assert store.validate(key)['valid']
        with pytest.raises(BusyError):
            with store.locked(key):pass
    model=next(a for a in bundle.artifacts if a.role=='model')
    (store.directory(key)/model.id).write_bytes(b'corrupt')
    with pytest.raises(ValueError):store.validate(key)


def test_cli_import_and_repeat(bundle_dir):
    seen=[]
    def handler(req):
        seen.append((req.method,req.url.path))
        if req.method=='PUT': assert req.read()
        return httpx.Response(200,json={'id':'test-id','status':'UPLOADING' if req.url.path.endswith('imports') else 'VALIDATED' if req.url.path.endswith('validate') else 'COMPLETED'})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result=import_bundle(client,'https://test/api/admin/sample-strategy-imports',bundle_dir)
    assert result['status']=='COMPLETED'
    assert seen[-1][1].endswith('/commit')
    assert sum(method=='PUT' for method,_ in seen)==6
    with httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'id':'test-id','status':'COMPLETED'}))) as client:
        assert import_bundle(client,'https://test/imports',bundle_dir)['status']=='COMPLETED'

@pytest.mark.parametrize('url',['http://evil.test','https://a:b@example.com','https://example.com?a=b','file:///tmp/x'])
def test_no_unsafe_api_url(url):
    with pytest.raises(ValueError):api_url(url)


def test_schema_and_verify_cli(bundle_dir,capsys):
    assert main(['schema'])==0
    assert 'schemaVersion' in json.loads(capsys.readouterr().out)['properties']
    assert main(['verify',str(bundle_dir)])==0
    assert json.loads(capsys.readouterr().out)['verified'] is True

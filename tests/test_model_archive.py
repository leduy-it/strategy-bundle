import hashlib
import json
import zipfile

import pytest

from promete_strategy_bundle.contract import verify_bundle
from promete_strategy_bundle.model_archive import check_policy_archive, write_policy_archive


def trained_style_archive(path):
    """Envelope of a saved off-policy SB3 model: training state next to the policy."""
    data = {
        'policy_class': {':type:': "<class 'abc.ABCMeta'>", ':serialized:': 'gAWV', '__module__': 'sb3_contrib.crossq.policies'},
        'observation_space': {':type:': "<class 'gymnasium.spaces.box.Box'>", ':serialized:': 'gAWV', '_shape': [4]},
        '_last_obs': {':type:': "<class 'numpy.ndarray'>", ':serialized:': 'gAWV'},
        'train_freq': {':type:': "<class 'stable_baselines3.common.type_aliases.TrainFreq'>", ':serialized:': 'gAWV'},
        'learning_rate': 0.001,
        'policy_kwargs': {'use_sde': False},
    }
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('data', json.dumps(data))
        archive.writestr('policy.pth', b'weights')
        archive.writestr('actor.optimizer.pth', b'optimizer')
        archive.writestr('_stable_baselines3_version', '2.9.0')


def test_policy_archive_keeps_only_what_the_server_accepts(tmp_path):
    trained_style_archive(tmp_path / 'trained.zip')
    with pytest.raises(ValueError, match='training-only members'):
        check_policy_archive(tmp_path / 'trained.zip')

    dropped = write_policy_archive(tmp_path / 'trained.zip', tmp_path / 'policy.zip')
    assert dropped == {'droppedMembers': ['actor.optimizer.pth'], 'droppedDataKeys': ['_last_obs', 'train_freq']}
    check_policy_archive(tmp_path / 'policy.zip')
    with zipfile.ZipFile(tmp_path / 'policy.zip') as archive:
        assert archive.namelist() == ['data', 'policy.pth', '_stable_baselines3_version']
        data = json.loads(archive.read('data'))
        assert archive.read('policy.pth') == b'weights'
    assert set(data) == {'policy_class', 'observation_space', 'learning_rate', 'policy_kwargs'}

    write_policy_archive(tmp_path / 'trained.zip', tmp_path / 'again.zip')
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(tmp_path / 'again.zip') == digest(tmp_path / 'policy.zip')


def test_verify_rejects_bundle_whose_model_still_has_training_state(bundle_dir):
    model = bundle_dir / 'model.zip'
    with zipfile.ZipFile(model, 'w') as archive:
        archive.writestr('data', json.dumps({'_last_obs': {':serialized:': 'gAWV'}}))
        archive.writestr('policy.pth', b'weights')
    manifest = json.loads((bundle_dir / 'manifest.json').read_text())
    entry = next(a for a in manifest['artifacts'] if a['role'] == 'model')
    entry.update(size=model.stat().st_size, sha256=hashlib.sha256(model.read_bytes()).hexdigest())
    (bundle_dir / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='serialized training state'):
        verify_bundle(bundle_dir)


def test_real_sb3_model_reduced_to_its_policy_predicts_the_same(tmp_path):
    np = pytest.importorskip('numpy')
    gym = pytest.importorskip('gymnasium')
    sb3 = pytest.importorskip('stable_baselines3')

    class Env(gym.Env):
        observation_space = gym.spaces.Box(-1, 1, (4,), np.float32)
        action_space = gym.spaces.Box(-1, 1, (2,), np.float32)

        def reset(self, *, seed=None, options=None):
            super().reset(seed=seed)
            return self.observation_space.sample(), {}

        def step(self, action):
            return self.observation_space.sample(), 0.0, True, False, {}

    model = sb3.SAC('MlpPolicy', Env(), buffer_size=16, learning_starts=1, batch_size=2, seed=3, device='cpu')
    model.learn(total_timesteps=8)
    model.save(tmp_path / 'trained.zip')
    with pytest.raises(ValueError):
        check_policy_archive(tmp_path / 'trained.zip')

    write_policy_archive(tmp_path / 'trained.zip', tmp_path / 'policy.zip')
    check_policy_archive(tmp_path / 'policy.zip')
    # Rebuild the policy only from what the reduced archive holds, as serving does.
    # (A full SB3 .load needs the optimizers to resume training; imports never resume.)
    from stable_baselines3.common.save_util import load_from_zip_file
    data, params, _ = load_from_zip_file(tmp_path / 'policy.zip', device='cpu')
    policy = data['policy_class'](data['observation_space'], data['action_space'], lambda _: 0.0,
                                  **data['policy_kwargs'])
    policy.load_state_dict(params['policy'])
    observation = np.full(4, 0.25, dtype=np.float32)
    expected, _ = model.predict(observation, deterministic=True)
    actual, _ = policy.predict(observation, deterministic=True)
    np.testing.assert_allclose(actual, expected, rtol=1e-6)

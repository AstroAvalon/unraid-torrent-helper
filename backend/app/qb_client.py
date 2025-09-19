# ==============================
# app/qb_client.py
# ==============================
import httpx
from typing import List, Dict, Any, Optional
from .config import AppConfig

class QBClient:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self._client = httpx.Client(base_url=str(cfg.qb_url), timeout=30.0)
        self._authed = False

    def login(self):
        if self._authed:
            return
        r = self._client.post('/api/v2/auth/login', data={'username': self.cfg.qb_username, 'password': self.cfg.qb_password})
        r.raise_for_status()
        if r.text != 'Ok.':
            raise RuntimeError('qBittorrent login failed')
        self._authed = True

    def _get(self, path: str, **kwargs):
        self.login()
        r = self._client.get(path, **kwargs)
        r.raise_for_status()
        return r

    def _post(self, path: str, **kwargs):
        self.login()
        r = self._client.post(path, **kwargs)
        r.raise_for_status()
        return r

    def list_torrents(self) -> List[Dict[str, Any]]:
        r = self._get('/api/v2/torrents/info', params={'filter': 'all'})
        return r.json()

    def pause(self, hashes: List[str]):
        self._post('/api/v2/torrents/pause', params={'hashes': '|'.join(hashes)})

    def resume(self, hashes: List[str]):
        self._post('/api/v2/torrents/resume', params={'hashes': '|'.join(hashes)})

    def set_location(self, hashes: List[str], location: str):
        self._post('/api/v2/torrents/setLocation', data={'hashes': '|'.join(hashes), 'location': location})

    def recheck(self, hashes: List[str]):
        self._post('/api/v2/torrents/recheck', params={'hashes': '|'.join(hashes)})

    def reannounce(self, hashes: List[str]):
        self._post('/api/v2/torrents/reannounce', params={'hashes': '|'.join(hashes)})

    def delete(self, hashes: List[str], delete_files: bool = False):
        self._post('/api/v2/torrents/delete', params={'hashes': '|'.join(hashes), 'deleteFiles': 'true' if delete_files else 'false'})

    def add_torrent(self, torrent_path: str, save_path: str, paused: bool = True, autoTMM: bool = False, root_folder: Optional[bool] = None):
        data = {
            'paused': 'true' if paused else 'false',
            'autoTMM': 'true' if autoTMM else 'false',
            'savepath': save_path,
        }
        if root_folder is not None:
            data['root_folder'] = 'true' if root_folder else 'false'
        files = {'torrents': (torrent_path.split('/')[-1], open(torrent_path, 'rb'), 'application/x-bittorrent')}
        r = self._post('/api/v2/torrents/add', data=data, files=files)
        return r.text

    def get_preferences(self) -> Dict[str, Any]:
        return self._get('/api/v2/app/preferences').json()

    def set_preferences(self, prefs: Dict[str, Any]):
        self._post('/api/v2/app/setPreferences', json=prefs)

import requests
from typing import Optional
from .base import BaseExtractor
from .schema import CodeforcesStats
from .mock_simulator import MockSimulator

class CodeforcesExtractor(BaseExtractor):
    API_URL = "https://codeforces.com/api/user.info"

    def extract(self, url_or_handle: str) -> Optional[CodeforcesStats]:
        username = self.extract_username(url_or_handle, 'codeforces')
        if not username:
            return None

        try:
            resp = requests.get(
                self.API_URL,
                params={'handles': username},
                headers=self.HEADERS,
                timeout=self.TIMEOUT
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'OK' and data.get('result'):
                    u = data['result'][0]
                    return CodeforcesStats(
                        username=username,
                        profile_url=f"https://codeforces.com/profile/{username}",
                        avatar_url=u.get('avatar', ''),
                        rating=u.get('rating', 0),
                        max_rating=u.get('maxRating', 0),
                        rank=u.get('rank', 'unrated'),
                        max_rank=u.get('maxRank', 'unrated'),
                        problems_solved=max(20, (u.get('rating', 0) // 10)),
                        contribution=u.get('contribution', 0),
                        is_simulated=False
                    )
        except Exception:
            pass

        return MockSimulator.simulate_codeforces(username)

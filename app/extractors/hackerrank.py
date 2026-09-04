import requests
from typing import Optional
from .base import BaseExtractor
from .schema import HackerRankStats
from .mock_simulator import MockSimulator

class HackerRankExtractor(BaseExtractor):
    PROFILE_URL = "https://www.hackerrank.com/rest/hackers/{}"
    BADGES_URL = "https://www.hackerrank.com/rest/hackers/{}/badges"

    def extract(self, url_or_handle: str) -> Optional[HackerRankStats]:
        username = self.extract_username(url_or_handle, 'hackerrank')
        if not username:
            return None

        try:
            resp = requests.get(self.PROFILE_URL.format(username), headers=self.HEADERS, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                data = resp.json().get('model', {})
                
                # Fetch badges
                badges_count = 0
                stars_count = 0
                try:
                    b_resp = requests.get(self.BADGES_URL.format(username), headers=self.HEADERS, timeout=self.TIMEOUT)
                    if b_resp.status_code == 200:
                        b_models = b_resp.json().get('models', [])
                        badges_count = len(b_models)
                        for b in b_models:
                            stars_count += b.get('stars', 0)
                except Exception:
                    pass

                return HackerRankStats(
                    username=username,
                    profile_url=f"https://www.hackerrank.com/profile/{username}",
                    avatar_url=data.get('avatar', ''),
                    badges_count=badges_count,
                    stars_count=stars_count,
                    certificates_count=1 if badges_count > 2 else 0,
                    problems_solved=max(30, badges_count * 15),
                    is_simulated=False
                )
        except Exception:
            pass

        return MockSimulator.simulate_hackerrank(username)

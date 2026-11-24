import re
import requests
from typing import Optional
from bs4 import BeautifulSoup
from .base import BaseExtractor
from .schema import CodingNinjasStats
from .mock_simulator import MockSimulator

class CodingNinjasExtractor(BaseExtractor):
    """Extractor for Coding Ninjas / CodeStudio / Naukri Code360 profiles."""

    API_URL = "https://api.codingninjas.com/api/v3/public_section/profile/user_details"

    def extract(self, url_or_handle: str) -> Optional[CodingNinjasStats]:
        username = self.extract_username(url_or_handle, 'codingninjas')
        if not username:
            return None

        profile_url = f"https://www.naukri.com/code360/profile/{username}"
        try:
            # First attempt public JSON API endpoint if available
            try:
                resp_api = requests.get(
                    f"{self.API_URL}?uuid={username}",
                    headers=self.HEADERS,
                    timeout=self.TIMEOUT
                )
                if resp_api.status_code == 200:
                    data = resp_api.json().get('data', {})
                    if data:
                        solved = int(data.get('problems_solved_count', 0) or data.get('solved_count', 0) or 0)
                        score = int(data.get('coding_score', 0) or data.get('total_points', 0) or 0)
                        streak = int(data.get('current_streak', 0) or 0)
                        rank = int(data.get('global_rank', 0) or 0)
                        badges = int(data.get('badges_count', 0) or len(data.get('badges', [])))
                        if solved > 0 or score > 0:
                            return CodingNinjasStats(
                                username=username,
                                profile_url=profile_url,
                                avatar_url=data.get('image_url') or f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
                                problems_solved=solved,
                                coding_score=score,
                                current_streak=streak,
                                global_rank=rank,
                                badges_count=badges,
                                is_simulated=False
                            )
            except Exception:
                pass

            # Fallback to HTML scraping
            resp = requests.get(profile_url, headers=self.HEADERS, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                text = resp.text
                soup = BeautifulSoup(text, 'html.parser')

                solved = 0
                score = 0
                streak = 0
                rank = 0
                badges = 0

                # Search stat cards or elements
                stat_elements = soup.find_all(['div', 'span', 'p'], class_=re.compile(r'stat|score|rank|streak|count|solved', re.I))
                for el in stat_elements:
                    t = el.get_text().strip().lower()
                    if 'problems solved' in t or 'problems' in t:
                        m = re.search(r'([\d,]+)', t)
                        if m:
                            solved = max(solved, int(m.group(1).replace(',', '')))
                    elif 'coding score' in t or 'points' in t or 'score' in t:
                        m = re.search(r'([\d,]+)', t)
                        if m:
                            score = max(score, int(m.group(1).replace(',', '')))
                    elif 'streak' in t:
                        m = re.search(r'(\d+)', t)
                        if m:
                            streak = max(streak, int(m.group(1)))
                    elif 'rank' in t:
                        m = re.search(r'([\d,]+)', t)
                        if m:
                            rank = max(rank, int(m.group(1).replace(',', '')))

                if solved > 0 or score > 0 or rank > 0:
                    return CodingNinjasStats(
                        username=username,
                        profile_url=profile_url,
                        avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
                        problems_solved=solved,
                        coding_score=score,
                        current_streak=streak,
                        global_rank=rank,
                        badges_count=badges,
                        is_simulated=False
                    )

            return MockSimulator.simulate_codingninjas(username)
        except Exception:
            return MockSimulator.simulate_codingninjas(username)

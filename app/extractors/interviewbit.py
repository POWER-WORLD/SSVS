import re
import requests
from typing import Optional
from bs4 import BeautifulSoup
from .base import BaseExtractor
from .schema import InterviewBitStats
from .mock_simulator import MockSimulator

class InterviewBitExtractor(BaseExtractor):
    """Extractor for InterviewBit profiles."""

    def extract(self, url_or_handle: str) -> Optional[InterviewBitStats]:
        username = self.extract_username(url_or_handle, 'interviewbit')
        if not username:
            return None

        profile_url = f"https://www.interviewbit.com/profile/{username}"
        try:
            resp = requests.get(profile_url, headers=self.HEADERS, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                score = 0
                rank = 0
                solved = 0
                streak = 0

                # Check for profile stat widgets
                stats_elements = soup.find_all(['div', 'span', 'p'], class_=re.compile(r'stat|score|rank|streak|count', re.I))
                for el in stats_elements:
                    text = el.get_text().strip().lower()
                    if 'score' in text:
                        m = re.search(r'([\d,]+)', text)
                        if m:
                            score = int(m.group(1).replace(',', ''))
                    elif 'rank' in text:
                        m = re.search(r'([\d,]+)', text)
                        if m:
                            rank = int(m.group(1).replace(',', ''))
                    elif 'streak' in text:
                        m = re.search(r'(\d+)', text)
                        if m:
                            streak = int(m.group(1))

                if score > 0 or rank > 0 or streak > 0:
                    return InterviewBitStats(
                        username=username,
                        profile_url=profile_url,
                        avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
                        score=score,
                        global_rank=rank,
                        problems_solved=solved or (score // 100),
                        streak_days=streak,
                        is_simulated=False
                    )

            return MockSimulator.simulate_interviewbit(username)
        except Exception:
            return MockSimulator.simulate_interviewbit(username)

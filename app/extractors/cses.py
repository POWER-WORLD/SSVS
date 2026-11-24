import re
import requests
from typing import Optional
from bs4 import BeautifulSoup
from .base import BaseExtractor
from .schema import CSESStats
from .mock_simulator import MockSimulator

class CSESExtractor(BaseExtractor):
    """Extractor for CSES Problem Set user profiles."""

    def extract(self, url_or_handle: str) -> Optional[CSESStats]:
        username = self.extract_username(url_or_handle, 'cses')
        if not username:
            return None

        profile_url = f"https://cses.fi/user/{username}"
        try:
            resp = requests.get(profile_url, headers=self.HEADERS, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                text = resp.text
                if 'User not found' in text or '404' in text:
                    return MockSimulator.simulate_cses(username)

                solved = 0
                total = 300

                # CSES profile HTML pattern: "Tasks solved: X / Y" or "Tasks solved: X"
                m_tasks = re.search(r'Tasks\s+solved\s*:\s*(\d+)(?:\s*\/\s*(\d+))?', text, re.I)
                if m_tasks:
                    solved = int(m_tasks.group(1))
                    if m_tasks.group(2):
                        total = int(m_tasks.group(2))
                else:
                    soup = BeautifulSoup(text, 'html.parser')
                    full_solved = soup.find_all('a', class_=re.compile(r'full|solved|task-score', re.I))
                    if full_solved:
                        solved = len(full_solved)
                    else:
                        m_num = re.search(r'solved\s*:\s*(\d+)', text, re.I)
                        if m_num:
                            solved = int(m_num.group(1))

                if solved > 0:
                    return CSESStats(
                        username=username,
                        profile_url=profile_url,
                        avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
                        problems_solved=solved,
                        total_problems=total,
                        is_simulated=False
                    )

            return MockSimulator.simulate_cses(username)
        except Exception:
            return MockSimulator.simulate_cses(username)

import re
import requests
from typing import Optional
from bs4 import BeautifulSoup
from .base import BaseExtractor
from .schema import KaggleStats
from .mock_simulator import MockSimulator

class KaggleExtractor(BaseExtractor):
    """Extractor for Kaggle data science profiles."""

    def extract(self, url_or_handle: str) -> Optional[KaggleStats]:
        username = self.extract_username(url_or_handle, 'kaggle')
        if not username:
            return None

        profile_url = f"https://www.kaggle.com/{username}"
        try:
            resp = requests.get(profile_url, headers=self.HEADERS, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                text = resp.text
                tier = "Contributor"
                medals = 0
                competitions = 0
                datasets = 0
                notebooks = 0

                # Check for Kaggle tier words
                for t in ['Grandmaster', 'Master', 'Expert', 'Contributor', 'Novice']:
                    if t.lower() in text.lower():
                        tier = t
                        break

                m_medals = re.findall(r'(\d+)\s*(?:Gold|Silver|Bronze|Medal)', text, re.I)
                if m_medals:
                    medals = sum(int(x) for x in m_medals)

                return KaggleStats(
                    username=username,
                    profile_url=profile_url,
                    avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
                    tier=tier,
                    total_medals=medals,
                    competitions_count=competitions,
                    datasets_count=datasets,
                    notebooks_count=notebooks,
                    is_simulated=False
                )

            return MockSimulator.simulate_kaggle(username)
        except Exception:
            return MockSimulator.simulate_kaggle(username)

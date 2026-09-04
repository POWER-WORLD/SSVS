import re
import requests
from typing import Optional
from bs4 import BeautifulSoup
from .base import BaseExtractor
from .schema import AtCoderStats
from .mock_simulator import MockSimulator

class AtCoderExtractor(BaseExtractor):
    """Extractor for AtCoder profiles."""

    def extract(self, url_or_handle: str) -> Optional[AtCoderStats]:
        username = self.extract_username(url_or_handle, 'atcoder')
        if not username:
            return None

        profile_url = f"https://atcoder.jp/users/{username}"
        try:
            resp = requests.get(profile_url, headers=self.HEADERS, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                rating = 0
                highest = 0
                rank = 0
                tier_color = "White"
                contests = 0

                # Rating table in AtCoder profile
                tables = soup.find_all('table', class_='dl-table')
                for table in tables:
                    for row in table.find_all('tr'):
                        th = row.find('th')
                        td = row.find('td')
                        if not th or not td:
                            continue
                        th_text = th.get_text().strip().lower()
                        td_text = td.get_text().strip()

                        if 'rating' in th_text and 'highest' not in th_text:
                            rating_span = td.find('span')
                            if rating_span:
                                r_val = re.search(r'\d+', rating_span.get_text())
                                if r_val:
                                    rating = int(r_val.group())
                                    # Color class
                                    c_class = rating_span.get('class', [])
                                    for c in c_class:
                                        if 'user-' in c:
                                            tier_color = c.replace('user-', '').capitalize()
                            else:
                                r_val = re.search(r'\d+', td_text)
                                if r_val:
                                    rating = int(r_val.group())
                        elif 'highest rating' in th_text:
                            h_val = re.search(r'\d+', td_text)
                            if h_val:
                                highest = int(h_val.group())
                        elif 'rank' in th_text:
                            rk_val = re.search(r'\d+', td_text.replace(',', ''))
                            if rk_val:
                                rank = int(rk_val.group())
                        elif 'rated matches' in th_text:
                            cm_val = re.search(r'\d+', td_text)
                            if cm_val:
                                contests = int(cm_val.group())

                if rating > 0 or highest > 0 or rank > 0:
                    return AtCoderStats(
                        username=username,
                        profile_url=profile_url,
                        avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
                        current_rating=rating,
                        highest_rating=max(highest, rating),
                        rank=rank,
                        tier_color=tier_color,
                        contests_attended=contests,
                        is_simulated=False
                    )

            # If profile page parsing yields 0 or fails, fallback to deterministic mock
            return MockSimulator.simulate_atcoder(username)
        except Exception:
            return MockSimulator.simulate_atcoder(username)

import re
import requests
from typing import Optional
from bs4 import BeautifulSoup
from .base import BaseExtractor
from .schema import TopCoderStats
from .mock_simulator import MockSimulator

class TopCoderExtractor(BaseExtractor):
    """Extractor for TopCoder competitive programming and development profiles."""

    API_V5_MEMBER = "https://api.topcoder.com/v5/members"

    def extract(self, url_or_handle: str) -> Optional[TopCoderStats]:
        username = self.extract_username(url_or_handle, 'topcoder')
        if not username:
            return None

        profile_url = f"https://profiles.topcoder.com/{username}"
        try:
            # Try TopCoder v5 REST API for member stats
            try:
                stats_url = f"{self.API_V5_MEMBER}/{username}/stats"
                resp_stats = requests.get(stats_url, headers=self.HEADERS, timeout=self.TIMEOUT)
                if resp_stats.status_code == 200:
                    stats_json = resp_stats.json()
                    # Parse algorithm / SRM stats
                    srm_data = stats_json.get('maxRating', {}) or {}
                    rating = int(stats_json.get('rating', 0) or srm_data.get('rating', 0) or 0)
                    highest = int(stats_json.get('highestRating', 0) or srm_data.get('highestRating', 0) or rating)
                    rank_name = "unrated"
                    if rating > 0:
                        if rating < 900:
                            rank_name = "Grey"
                        elif rating < 1200:
                            rank_name = "Green"
                        elif rating < 1500:
                            rank_name = "Blue"
                        elif rating < 2200:
                            rank_name = "Yellow"
                        else:
                            rank_name = "Red"

                    competitions = int(stats_json.get('competitions', 0) or 0)
                    solved = int(stats_json.get('problemsSolved', 0) or 0)

                    if rating > 0 or solved > 0:
                        return TopCoderStats(
                            username=username,
                            profile_url=profile_url,
                            avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
                            rating=rating,
                            highest_rating=highest,
                            rank=rank_name,
                            competitions_count=competitions,
                            problems_solved=solved,
                            is_simulated=False
                        )
            except Exception:
                pass

            # Fallback to HTML scraping
            resp = requests.get(profile_url, headers=self.HEADERS, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                text = resp.text
                soup = BeautifulSoup(text, 'html.parser')

                rating = 0
                highest = 0
                rank_name = "unrated"
                competitions = 0
                solved = 0

                # Search rating and rank
                m_rating = re.search(r'Rating[\s:]*([0-9]{3,4})', text, re.I)
                if m_rating:
                    rating = int(m_rating.group(1))
                    highest = rating

                m_high = re.search(r'Highest\s+Rating[\s:]*([0-9]{3,4})', text, re.I)
                if m_high:
                    highest = int(m_high.group(1))

                if rating > 0:
                    if rating < 900:
                        rank_name = "Grey"
                    elif rating < 1200:
                        rank_name = "Green"
                    elif rating < 1500:
                        rank_name = "Blue"
                    elif rating < 2200:
                        rank_name = "Yellow"
                    else:
                        rank_name = "Red"

                    return TopCoderStats(
                        username=username,
                        profile_url=profile_url,
                        avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
                        rating=rating,
                        highest_rating=highest,
                        rank=rank_name,
                        competitions_count=competitions,
                        problems_solved=solved,
                        is_simulated=False
                    )

            return MockSimulator.simulate_topcoder(username)
        except Exception:
            return MockSimulator.simulate_topcoder(username)

import re
import requests
from typing import Optional
from bs4 import BeautifulSoup
from .base import BaseExtractor
from .schema import SpojStats
from .mock_simulator import MockSimulator

class SpojExtractor(BaseExtractor):
    """Extractor for Sphere Online Judge (SPOJ) user profiles."""

    def extract(self, url_or_handle: str) -> Optional[SpojStats]:
        username = self.extract_username(url_or_handle, 'spoj')
        if not username:
            return None

        profile_url = f"https://www.spoj.com/users/{username}/"
        try:
            resp = requests.get(profile_url, headers=self.HEADERS, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                text = resp.text

                # Check if user does not exist
                if 'user does not exist' in text.lower() or 'no such user' in text.lower():
                    return MockSimulator.simulate_spoj(username)

                problems_solved = 0
                points = 0.0
                world_rank = 0
                solutions_submitted = 0

                # Search dl/dt/dd or table cells for profile data
                m_solved = re.search(r'Problems solved[\s:]*</td>\s*<td[^>]*>(\d+)', text, re.I)
                if not m_solved:
                    m_solved = re.search(r'Problems solved[\s:]*</(?:dt|strong|b)>\s*<(?:dd|span)[^>]*>(\d+)', text, re.I)
                if not m_solved:
                    m_solved = re.search(r'Problems\s+solved\s*:\s*(\d+)', text, re.I)
                if not m_solved:
                    # Count solved problem links in tables
                    tables = soup.find_all('table', class_=re.compile(r'problems|table', re.I))
                    for table in tables:
                        links = table.find_all('a', href=re.compile(r'/status/|/problems/'))
                        if links:
                            problems_solved = max(problems_solved, len(links))

                if m_solved:
                    problems_solved = int(m_solved.group(1))

                # Points
                m_points = re.search(r'Points[\s:]*</td>\s*<td[^>]*>([\d.]+)', text, re.I)
                if not m_points:
                    m_points = re.search(r'Points[\s:]*</(?:dt|strong|b)>\s*<(?:dd|span)[^>]*>([\d.]+)', text, re.I)
                if not m_points:
                    m_points = re.search(r'([\d.]+)\s*points?', text, re.I)
                if m_points:
                    try:
                        points = float(m_points.group(1))
                    except ValueError:
                        points = 0.0

                # World rank
                m_rank = re.search(r'World\s+rank[\s:]*</td>\s*<td[^>]*>#?([\d,]+)', text, re.I)
                if not m_rank:
                    m_rank = re.search(r'World\s+rank[\s:]*</(?:dt|strong|b)>\s*<(?:dd|span)[^>]*>#?([\d,]+)', text, re.I)
                if not m_rank:
                    m_rank = re.search(r'World\s+Rank\s*:\s*#?([\d,]+)', text, re.I)
                if m_rank:
                    try:
                        world_rank = int(m_rank.group(1).replace(',', ''))
                    except ValueError:
                        world_rank = 0

                # Solutions submitted
                m_sol = re.search(r'Solutions\s+submitted[\s:]*</td>\s*<td[^>]*>([\d,]+)', text, re.I)
                if not m_sol:
                    m_sol = re.search(r'Solutions\s+submitted[\s:]*</(?:dt|strong|b)>\s*<(?:dd|span)[^>]*>([\d,]+)', text, re.I)
                if not m_sol:
                    m_sol = re.search(r'Solutions\s+submitted\s*:\s*([\d,]+)', text, re.I)
                if m_sol:
                    try:
                        solutions_submitted = int(m_sol.group(1).replace(',', ''))
                    except ValueError:
                        solutions_submitted = 0

                if problems_solved > 0 or points > 0.0 or world_rank > 0:
                    return SpojStats(
                        username=username,
                        profile_url=profile_url,
                        avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
                        problems_solved=problems_solved,
                        points=points,
                        world_rank=world_rank,
                        solutions_submitted=solutions_submitted or problems_solved,
                        is_simulated=False
                    )

            return MockSimulator.simulate_spoj(username)
        except Exception:
            return MockSimulator.simulate_spoj(username)

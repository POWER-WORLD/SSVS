import re
import requests
from bs4 import BeautifulSoup
from typing import Optional
from .base import BaseExtractor
from .schema import CodeChefStats
from .mock_simulator import MockSimulator

class CodeChefExtractor(BaseExtractor):
    BASE_URL = "https://www.codechef.com/users/{}"

    def extract(self, url_or_handle: str) -> Optional[CodeChefStats]:
        username = self.extract_username(url_or_handle, 'codechef')
        if not username:
            return None

        url = self.BASE_URL.format(username)
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=self.TIMEOUT)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Rating header
                rating_div = soup.find('div', class_='rating-number')
                current_rating = int(rating_div.text.strip()) if rating_div else 0
                
                # Highest rating
                highest_rating = current_rating
                small_tag = soup.find('small')
                if small_tag and 'Highest Rating' in small_tag.text:
                    m = re.search(r'Highest Rating\s*(\d+)', small_tag.text)
                    if m:
                        highest_rating = int(m.group(1))
                        
                # Stars
                stars_span = soup.find('span', class_='rating')
                stars = 0
                if stars_span:
                    stars_text = stars_span.text.strip()
                    stars = len(stars_text.replace('★', 'x')) if '★' in stars_text else 0
                if stars == 0 and current_rating > 0:
                    if current_rating >= 2000:
                        stars = 5
                    elif current_rating >= 1800:
                        stars = 4
                    elif current_rating >= 1600:
                        stars = 3
                    elif current_rating >= 1400:
                        stars = 2
                    else:
                        stars = 1
                        
                # Global / Country ranks
                ranks = soup.find_all('strong', class_='global-rank')
                global_rank = 0
                if ranks:
                    global_rank = int(ranks[0].text.strip().replace(',', ''))
                    
                # Solved count
                solved_section = soup.find('section', class_='problems-solved')
                solved_count = 0
                if solved_section:
                    h3s = solved_section.find_all('h3')
                    for h3 in h3s:
                        m = re.search(r'Total Problems Solved:\s*(\d+)', h3.text)
                        if m:
                            solved_count = int(m.group(1))
                            break

                return CodeChefStats(
                    username=username,
                    profile_url=url,
                    avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
                    current_rating=current_rating,
                    highest_rating=highest_rating,
                    stars=stars,
                    global_rank=global_rank,
                    problems_solved=solved_count,
                    is_simulated=False
                )
        except Exception:
            pass

        return MockSimulator.simulate_codechef(username)

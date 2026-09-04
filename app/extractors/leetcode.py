import requests
from typing import Optional
from .base import BaseExtractor
from .schema import LeetCodeStats
from .mock_simulator import MockSimulator

class LeetCodeExtractor(BaseExtractor):
    GRAPHQL_URL = "https://leetcode.com/graphql"

    def extract(self, url_or_handle: str) -> Optional[LeetCodeStats]:
        username = self.extract_username(url_or_handle, 'leetcode')
        if not username:
            return None

        query = """
        query getUserProfile($username: String!) {
          matchedUser(username: $username) {
            username
            profile {
              ranking
              userAvatar
            }
            submitStats {
              acSubmissionNum {
                difficulty
                count
              }
            }
            badges {
              id
            }
          }
          userContestRanking(username: $username) {
            attendedContestsCount
            rating
            globalRanking
          }
        }
        """
        
        try:
            resp = requests.post(
                self.GRAPHQL_URL,
                json={'query': query, 'variables': {'username': username}},
                headers={**self.HEADERS, 'Referer': f'https://leetcode.com/{username}'},
                timeout=self.TIMEOUT
            )
            
            if resp.status_code == 200:
                data = resp.json().get('data', {})
                matched_user = data.get('matchedUser')
                if matched_user:
                    profile = matched_user.get('profile', {}) or {}
                    submit_stats = matched_user.get('submitStats', {}).get('acSubmissionNum', [])
                    contest = data.get('userContestRanking') or {}
                    
                    easy = medium = hard = total = 0
                    for item in submit_stats:
                        diff = item.get('difficulty')
                        cnt = item.get('count', 0)
                        if diff == 'All':
                            total = cnt
                        elif diff == 'Easy':
                            easy = cnt
                        elif diff == 'Medium':
                            medium = cnt
                        elif diff == 'Hard':
                            hard = cnt
                            
                    badges = matched_user.get('badges') or []
                    
                    return LeetCodeStats(
                        username=username,
                        profile_url=f"https://leetcode.com/u/{username}/",
                        avatar_url=profile.get('userAvatar', ''),
                        total_solved=total,
                        easy_solved=easy,
                        medium_solved=medium,
                        hard_solved=hard,
                        contest_rating=round(float(contest.get('rating', 0.0)), 1),
                        global_rank=contest.get('globalRanking') or profile.get('ranking') or 0,
                        contests_attended=contest.get('attendedContestsCount', 0),
                        badges_count=len(badges),
                        is_simulated=False
                    )
        except Exception as e:
            # Log error and use simulator fallback
            pass

        return MockSimulator.simulate_leetcode(username)

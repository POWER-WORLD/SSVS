from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .schema import (
    UnifiedStudentStats,
    LeetCodeStats,
    CodeChefStats,
    CodeforcesStats,
    GitHubStats,
    HackerRankStats,
    GeeksforGeeksStats,
    AtCoderStats,
    InterviewBitStats,
    KaggleStats,
    SpojStats,
    CodingNinjasStats,
    CSESStats,
    TopCoderStats
)
from .base import BaseExtractor
from .leetcode import LeetCodeExtractor
from .codechef import CodeChefExtractor
from .codeforces import CodeforcesExtractor
from .github import GitHubExtractor
from .hackerrank import HackerRankExtractor
from .geeksforgeeks import GeeksforGeeksExtractor
from .atcoder import AtCoderExtractor
from .interviewbit import InterviewBitExtractor
from .kaggle import KaggleExtractor
from .spoj import SpojExtractor
from .codingninjas import CodingNinjasExtractor
from .cses import CSESExtractor
from .topcoder import TopCoderExtractor
from .mock_simulator import MockSimulator

# Registry of supported platforms
EXTRACTORS = {
    'leetcode': LeetCodeExtractor(),
    'codechef': CodeChefExtractor(),
    'codeforces': CodeforcesExtractor(),
    'github': GitHubExtractor(),
    'hackerrank': HackerRankExtractor(),
    'gfg': GeeksforGeeksExtractor(),
    'geeksforgeeks': GeeksforGeeksExtractor(),
    'atcoder': AtCoderExtractor(),
    'interviewbit': InterviewBitExtractor(),
    'kaggle': KaggleExtractor(),
    'spoj': SpojExtractor(),
    'codingninjas': CodingNinjasExtractor(),
    'coding_ninjas': CodingNinjasExtractor(),
    'cses': CSESExtractor(),
    'topcoder': TopCoderExtractor()
}

def extract_all_profiles(handles: Dict[str, str], cgpa: float = 0.0, backlogs: int = 0) -> UnifiedStudentStats:
    """
    Extract statistics for all provided platform handles concurrently.
    
    handles: dictionary mapping platform name to handle or URL:
      e.g. {'leetcode': 'neal_wu', 'github': 'https://github.com/octocat', 'atcoder': 'tourist'}
    """
    stats = UnifiedStudentStats(cgpa=cgpa, backlogs=backlogs)
    
    def run_single(platform: str, val: str):
        extractor = EXTRACTORS.get(platform.lower())
        if extractor and val:
            try:
                return platform, extractor.extract(val)
            except Exception:
                return platform, None
        return platform, None

    # Run network calls concurrently using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(run_single, p, h) for p, h in handles.items() if h]
        for future in as_completed(futures):
            try:
                platform, result = future.result()
                if result:
                    if platform == 'leetcode':
                        stats.leetcode = result
                    elif platform == 'codechef':
                        stats.codechef = result
                    elif platform == 'codeforces':
                        stats.codeforces = result
                    elif platform == 'github':
                        stats.github = result
                    elif platform == 'hackerrank':
                        stats.hackerrank = result
                    elif platform in ('gfg', 'geeksforgeeks'):
                        stats.gfg = result
                    elif platform == 'atcoder':
                        stats.atcoder = result
                    elif platform == 'interviewbit':
                        stats.interviewbit = result
                    elif platform == 'kaggle':
                        stats.kaggle = result
                    elif platform == 'spoj':
                        stats.spoj = result
                    elif platform in ('codingninjas', 'coding_ninjas'):
                        stats.codingninjas = result
                    elif platform == 'cses':
                        stats.cses = result
                    elif platform == 'topcoder':
                        stats.topcoder = result
            except Exception:
                pass

    return stats

from __future__ import annotations
import collections
from typing import List, Dict, Optional
from phase1.models import Restaurant, BudgetBand, Preferences
from phase1.filtering import filter_hard_constraints, build_fallback_policy

class IndexedRestaurantStore:
    def __init__(self, restaurants: List[Restaurant]):
        self.restaurants = restaurants
        self.by_location: Dict[str, List[Restaurant]] = collections.defaultdict(list)
        
        # Build index
        for r in restaurants:
            if r.location:
                # lowercase for case-insensitive lookup
                self.by_location[r.location.casefold().strip()].append(r)
                
    def _get_by_location(self, location: Optional[str]) -> List[Restaurant]:
        if not location:
            return self.restaurants
        
        loc_key = location.casefold().strip()
        return self.by_location.get(loc_key, [])

    def filter_hard_constraints_indexed(self, prefs: Preferences) -> List[Restaurant]:
        # Fast retrieval by location (O(1) lookup instead of O(N) scan)
        candidates = self._get_by_location(prefs.location)
        
        # Apply the rest of the constraints linearly on the much smaller subset
        return filter_hard_constraints(candidates, prefs)

    def generate_candidates(
        self,
        prefs: Preferences,
        min_candidates: int = 20,
    ) -> tuple[List[Restaurant], List[str], Preferences]:
        relaxations: list[str] = []
        current = prefs

        candidates = self.filter_hard_constraints_indexed(current)
        if len(candidates) >= min_candidates or len(candidates) > 0:
            return candidates, relaxations, current

        for step in build_fallback_policy(current):
            current = step.transform(current)
            relaxations.append(step.name)
            candidates = self.filter_hard_constraints_indexed(current)
            if len(candidates) >= min_candidates or len(candidates) > 0:
                return candidates, relaxations, current

        return candidates, relaxations, current

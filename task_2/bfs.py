from collections import deque

class PetriNet:
    def __init__(self, places, transitions, arcs):
        self.place_ids = list(places.keys())
        self.initial_marking = tuple(places[p] for p in self.place_ids)

        # build pre/post incidence
        self.pre = {t: set() for t in transitions}
        self.post = {t: set() for t in transitions}

        for s, t in arcs:
            if s in places and t in transitions:
                self.pre[t].add(s)
            elif s in transitions and t in places:
                self.post[s].add(t)

    def fire(self, marking, transition):
        new_m = list(marking)

        # Check enabled
        for p in self.pre[transition]:
            i = self.place_ids.index(p)
            if new_m[i] == 0:
                return None  # not enabled

        # consume tokens
        for p in self.pre[transition]:
            i = self.place_ids.index(p)
            new_m[i] = 0

        # produce tokens
        for p in self.post[transition]:
            i = self.place_ids.index(p)
            if new_m[i] == 1:
                return None  # 1-safe violation
            new_m[i] = 1

        return tuple(new_m)

    def reachable_markings_bfs(self):
        visited = set()
        queue = deque([self.initial_marking])
        visited.add(self.initial_marking)

        while queue:
            m = queue.popleft()
            for t in self.pre:
                new_m = self.fire(m, t)
                if new_m is not None and new_m not in visited:
                    visited.add(new_m)
                    queue.append(new_m)

        return visited
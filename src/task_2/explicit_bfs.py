from collections import deque

class PetriNet:
    def __init__(self, places, transitions, arcs):
        self.place_ids = sorted(list(places.keys()))
        
        self.p_indices = {pid: i for i, pid in enumerate(self.place_ids)} 
        
        self.initial_marking = tuple(places[p] for p in self.place_ids)

        self.pre = {t: set() for t in transitions}
        self.post = {t: set() for t in transitions}

        for s, t in arcs:
            if s in places and t in transitions:
                self.pre[t].add(s)
            elif s in transitions and t in places:
                self.post[s].add(t)

    def fire(self, marking, transition):
        new_m = list(marking)

        for p in self.pre[transition]:
            idx = self.p_indices[p] 
            if new_m[idx] == 0:
                return None 

        for p in self.pre[transition]:
            idx = self.p_indices[p]
            new_m[idx] = 0 

        for p in self.post[transition]:
            idx = self.p_indices[p]
            if new_m[idx] == 1:
                return None 
            new_m[idx] = 1 

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

# -----------------------------
# Efficient explicit BFS using bitmasks
# -----------------------------
class PetriNetBitmask:
    """
    Efficient 1-safe Petri net forward exploration using integer bitmasks.
    Each place -> one bit in an integer (LSB = place_ids[0]).
    """
    def __init__(self, places, transitions, arcs):
        self.place_ids = sorted(list(places.keys()))
        self.p_indices = {pid: i for i, pid in enumerate(self.place_ids)}
        self.num_places = len(self.place_ids)

        im = 0
        for pid, tokens in places.items():
            if tokens and tokens > 0:
                im |= (1 << self.p_indices[pid])
        self.initial_mask = im

        self.transitions = sorted(list(transitions))
        self.pre_mask = {}
        self.post_mask = {}
        for t in self.transitions:
            self.pre_mask[t] = 0
            self.post_mask[t] = 0

        for s, t in arcs:
            if s in places and t in transitions:
                self.pre_mask[t] |= (1 << self.p_indices[s])
            elif s in transitions and t in places:
                self.post_mask[s] |= (1 << self.p_indices[t])

    def fire_mask(self, marking_mask, transition):
        """
        Return next_mask (int) if enabled and 1-safe preserved, otherwise None.
        Logic:
          - enabled iff (marking & pre_mask) == pre_mask
          - 1-safe violation iff there exists a post-only place already 1:
              (marking & (post_mask & ~pre_mask)) != 0
          - next = (marking & ~pre_mask) | post_mask
        This handles read/loop places (both pre & post) correctly.
        """
        pre = self.pre_mask[transition]
        post = self.post_mask[transition]

        if (marking_mask & pre) != pre:
            return None

        post_only = post & (~pre)
        if (marking_mask & post_only) != 0:
            return None  # would violate 1-safe

        next_mask = (marking_mask & (~pre)) | post
        return next_mask

    def reachable_markings_bfs(self, limit=None):
        """
        BFS returning a set of integer masks.
        limit: optional cap on number of reachable markings to explore (None => unlimited).
        """
        from collections import deque
        q = deque([self.initial_mask])
        visited = {self.initial_mask}
        while q:
            m = q.popleft()
            for t in self.transitions:
                nm = self.fire_mask(m, t)
                if nm is not None and nm not in visited:
                    visited.add(nm)
                    q.append(nm)
                    if limit is not None and len(visited) >= limit:
                        return visited
        return visited

    def mask_to_tuple(self, mask):
        return tuple(1 if (mask >> i) & 1 else 0 for i in range(self.num_places))

def build_bdd_from_int_markings(bdd_obj, vars_x, markings_int):
    """
    bdd_obj: dd.BDD instance
    vars_x: list of variable names corresponding to place indices
    markings_int: iterable of integer masks
    Returns a BDD encoding the union of those markings.
    """
    bdd_all = bdd_obj.false
    for mask in markings_int:
        conj = bdd_obj.true
        for i, var in enumerate(vars_x):
            v = bdd_obj.var(var)
            if (mask >> i) & 1:
                conj = bdd_obj.apply('and', conj, v)
            else:
                conj = bdd_obj.apply('and', conj, bdd_obj.apply('not', v))
        bdd_all = bdd_obj.apply('or', bdd_all, conj)
    return bdd_all
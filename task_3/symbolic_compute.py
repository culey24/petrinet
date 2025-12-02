import time
from dd.bdd import BDD

class SymbolicPetriNet:
    def __init__(self, places, transitions, arcs):
        self.b = BDD()

        # consistent place ordering
        self.places = sorted(list(places.keys()))
        self.num_places = len(self.places)
        self.place_ids = self.places
        self.transitions = list(transitions)

        # variable names
        self.var_names = [f'x{i}' for i in range(self.num_places)]
        self.var_names_p = [f'xp{i}' for i in range(self.num_places)]

        # declare variables in the manager
        self.b.declare(*(self.var_names + self.var_names_p))

        # variables as nodes (manager.var returns a BDD node id)
        self.vars_x = [self.b.var(name) for name in self.var_names]
        self.vars_xp = [self.b.var(name) for name in self.var_names_p]

        self.p_map = {pid: i for i, pid in enumerate(self.places)}

        # initial marking BDD
        self.init_bdd = self.b.true
        for pid, tokens in places.items():
            idx = self.p_map[pid]
            if tokens == 1:
                self.init_bdd = self.b.apply('and', self.init_bdd, self.vars_x[idx])
            else:
                neg = self.b.apply('not', self.vars_x[idx])
                self.init_bdd = self.b.apply('and', self.init_bdd, neg)

        # build pre/post
        self.pre = {t: set() for t in self.transitions}
        self.post = {t: set() for t in self.transitions}
        for s, t in arcs:
            if t in self.transitions:
                self.pre[t].add(s)
            elif s in self.transitions:
                self.post[s].add(t)
    def _count_bdd(self, node):
        """
        Count number of satisfying assignments using dd 0.6.0.
        """
        try:
            c = self.b.count(node, self.num_places)
            return int(round(c))
        except Exception as e:
            raise RuntimeError(f"BDD count failed: {e}")

    def build_transition_relation(self):
        R_total = self.b.false
        for t in self.transitions:
            cond_enabled = self.b.true
            involved = self.pre[t].union(self.post[t])

            # enabled: all pre places must be 1
            for p in self.pre[t]:
                idx = self.p_map[p]
                cond_enabled = self.b.apply('and', cond_enabled, self.vars_x[idx])

            # action on next-state vars
            action = self.b.true
            for p in self.pre[t]:
                idx = self.p_map[p]
                if p not in self.post[t]:
                    neg_xp = self.b.apply('not', self.vars_xp[idx])
                    action = self.b.apply('and', action, neg_xp)
            for p in self.post[t]:
                idx = self.p_map[p]
                if p not in self.pre[t]:
                    action = self.b.apply('and', action, self.vars_xp[idx])

            # frame: unaffected places x_i == x_i'
            frame = self.b.true
            for pid in self.place_ids:
                if pid not in involved:
                    idx = self.p_map[pid]
                    xor_expr = self.b.apply('xor', self.vars_x[idx], self.vars_xp[idx])
                    xnor = self.b.apply('not', xor_expr)
                    frame = self.b.apply('and', frame, xnor)

            R_t = self.b.apply('and', cond_enabled, self.b.apply('and', action, frame))
            R_total = self.b.apply('or', R_total, R_t)

        return R_total

    def build_bdd_from_markings(self, markings):
        """Construct a BDD (over x0,x1,..) that is true exactly on the given markings (iterable of tuples)."""
        S = self.b.false
        for m in markings:
            term = self.b.true
            for i, bit in enumerate(m):
                if bit == 1:
                    term = self.b.apply('and', term, self.vars_x[i])
                else:
                    term = self.b.apply('and', term, self.b.apply('not', self.vars_x[i]))
            S = self.b.apply('or', S, term)
        return S

    def compute_reachable(self, fallback_markings=None):
        """
        Try symbolic fixed-point using manager.exist if available.
        If that API isn't present or is difficult, you can supply
        fallback_markings (list of tuples) and we'll build the BDD directly.
        """
        # Fast path: if caller provided explicit markings (from your BFS), build BDD from them
        if fallback_markings is not None:
            S = self.build_bdd_from_markings(fallback_markings)
            count = self._count_bdd(S)

            return S, int(round(count)), 0.0

        # Otherwise try the symbolic fixed point (best-effort; depends on dd version)
        R = self.build_transition_relation()
        S = self.init_bdd

        # attempt to call manager.exist if available
        try:
            # quant vars by name
            qvars = set(self.var_names)
            while True:
                SR = self.b.apply('and', S, R)
                # use manager's exist if present: signature may be (vars, node)
                img_xp = self.b.exist(qvars, SR)
                # rename x' -> x using manager.let; map xp names to x names
                rename_map = {self.var_names_p[i]: self.var_names[i] for i in range(self.num_places)}
                img_x = self.b.let(rename_map, img_xp)
                S_new = self.b.apply('or', S, img_x)
                if S_new == S:
                    break
                S = S_new
            count = self._count_bdd(S)

            return S, int(round(count)), 0.0
        except Exception as e:
            raise RuntimeError("Symbolic iteration failed; please either use a dd version with 'exist' or pass explicit reachable "
                                "markings (fallback_markings) computed by BFS. Original error: " + str(e))
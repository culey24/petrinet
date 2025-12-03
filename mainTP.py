import xml.etree.ElementTree as ET
from collections import deque
import time

# Ensure you have installed the library: pip install dd
from dd.bdd import BDD

# ==========================================================
# Task 1 — PNML Parser + Consistency Checker
# ==========================================================

class PNMLParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.places = {} 
        self.transitions = set()
        self.arcs = []

    def parse(self):
        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
        except FileNotFoundError:
            print(f"Error: File '{self.file_path}' not found.")
            return self

        # --- FIX: Strip Namespaces ---
        # The PNML file uses a namespace (xmlns="..."). 
        # We strip it from every tag to make searching easy.
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
        # -----------------------------

        net = root.find("net")
        if net is None:
            print("Error: Could not find <net> element. Check XML structure.")
            return self

        # ---- Places ----
        for place in net.findall(".//place"):
            pid = place.attrib["id"]
            # Handle potential missing initialMarking
            marking_el = place.find(".//initialMarking/text") 
            if marking_el is not None and marking_el.text:
                marking = int(marking_el.text)
            else:
                marking = 0
            self.places[pid] = marking

        # ---- Transitions ----
        for transition in net.findall(".//transition"):
            tid = transition.attrib["id"]
            self.transitions.add(tid)

        # ---- Arcs ----
        for arc in net.findall(".//arc"):
            source = arc.attrib["source"]
            target = arc.attrib["target"]
            self.arcs.append((source, target))

        return self

    def validate(self):
        errors = []
        if not self.places and not self.transitions:
            errors.append("Net is empty (Parsing failed or empty file).")
            return errors

        # Check sources/targets exist
        for s, t in self.arcs:
            if s not in self.places and s not in self.transitions:
                errors.append(f"Arc source '{s}' does not exist")
            if t not in self.places and t not in self.transitions:
                errors.append(f"Arc target '{t}' does not exist")

        # Check arc direction (no place->place, no trans->trans)
        for s, t in self.arcs:
            if s in self.places and t in self.places:
                errors.append(f"Invalid arc place→place: {s}→{t}")
            if s in self.transitions and t in self.transitions:
                errors.append(f"Invalid arc transition→transition: {s}→{t}")

        return errors


# ==========================================================
# Task 2 — Reachability Graph (BFS)
# ==========================================================

from collections import deque

class PetriNet:
    def __init__(self, places, transitions, arcs):
        # 1. Ensure deterministic order
        self.place_ids = sorted(list(places.keys()))
        
        # 2. FIX: Create an O(1) lookup map for indices
        self.p_indices = {pid: i for i, pid in enumerate(self.place_ids)} 
        
        self.initial_marking = tuple(places[p] for p in self.place_ids)

        # build pre/post incidence
        self.pre = {t: set() for t in transitions}
        self.post = {t: set() for t in transitions}

        for s, t in arcs:
            if s in places and t in transitions:
                self.pre[t].add(s)
            elif s in transitions and t in places:
                self.post[s].add(t)

    # This fire method is strictly for 1-safe nets (Boolean)
    def fire(self, marking, transition):
        new_m = list(marking)

        # Check enabled
        for p in self.pre[transition]:
            # FIX: Use O(1) dictionary lookup
            idx = self.p_indices[p] 
            if new_m[idx] == 0:
                return None  # not enabled

        # consume tokens
        for p in self.pre[transition]:
            # FIX: Use O(1) dictionary lookup
            idx = self.p_indices[p]
            new_m[idx] = 0 # consumes token

        # produce tokens
        for p in self.post[transition]:
            # FIX: Use O(1) dictionary lookup
            idx = self.p_indices[p]
            if new_m[idx] == 1:
                return None  # 1-safe violation
            new_m[idx] = 1 # produces token

        return tuple(new_m)
        
    def reachable_markings_bfs(self):
        visited = set()
        queue = deque([self.initial_marking])
        visited.add(self.initial_marking)

        while queue:
            m = queue.popleft()
            # Iterate through transitions, check if firing is possible/valid
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

        # initial marking as int bitmask
        im = 0
        for pid, tokens in places.items():
            if tokens and tokens > 0:
                im |= (1 << self.p_indices[pid])
        self.initial_mask = im

        # prepare transition masks
        self.transitions = sorted(list(transitions))
        # pre_mask[t] and post_mask[t] stored by transition id
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

        # enabled?
        if (marking_mask & pre) != pre:
            return None

        # producing into already-full, but only for post-only places:
        post_only = post & (~pre)
        if (marking_mask & post_only) != 0:
            return None  # would violate 1-safe

        # compute next
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

    # helper to pretty-print a mask as tuple like before (0/1 tuple)
    def mask_to_tuple(self, mask):
        return tuple(1 if (mask >> i) & 1 else 0 for i in range(self.num_places))


# -----------------------------
# Small helper to build BDD from int-markings (only used as fallback / optional)
# -----------------------------
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
# =============================================================================
# TASK 3: SYMBOLIC REACHABILITY (BDD)
# =============================================================================

import time
from dd.bdd import BDD

# =============================================================================
# TASK 3: SYMBOLIC REACHABILITY (BDD)
# Refined Implementation for Correctness and Assignment Compliance
# =============================================================================

def symbolic_reachability(places, transitions):
    """
    Computes the set of reachable markings using Binary Decision Diagrams (BDD).
    
    CORRECTION: Uses bdd.apply() instead of operators &, |, ~ because 
    'dd.bdd' returns integers, and Python bitwise operators corrupt the BDD node IDs.
    """
    print("\n[Symbolic BDD] Starting BDD construction...")
    start_time = time.time()
    
    # 1. Initialize BDD Manager
    bdd = BDD()
    
    # --- HELPER FUNCTIONS FOR SAFTEY ---
    # Wraps bdd.apply to avoid using &, |, ~ on integers
    def AND(u, v): return bdd.apply('and', u, v)
    def OR(u, v):  return bdd.apply('or', u, v)
    def NOT(u):    return bdd.apply('not', u)
    def DIFF(u, v): return bdd.apply('diff', u, v)
    # -----------------------------------

    num_places = len(places)
    
    # 2. Variable Declaration (Interleaved for Optimization)
    var_order = []
    for i in range(num_places):
        var_order.append(f"x{i}") # Current state
        var_order.append(f"y{i}") # Next state
    
    bdd.declare(*var_order)
    
    # x[i] and y[i] are integers representing BDD nodes
    x = [bdd.var(f"x{i}") for i in range(num_places)]
    y = [bdd.var(f"y{i}") for i in range(num_places)]
    
    # 3. Construct Initial Marking I(x)
    print("  [BDD] Encoding Initial Marking...")
    init_bdd = bdd.true
    
    # places is a dict {id: tokens}, sorted keys match indices 0..N-1
    sorted_pids = sorted(places.keys())
    
    for i, pid in enumerate(sorted_pids):
        if places[pid] == 1:
            init_bdd = AND(init_bdd, x[i])
        else:
            init_bdd = AND(init_bdd, NOT(x[i]))
            
    # 4. Construct Transition Relation T(x, y)
    print("  [BDD] Constructing Transition Relations...")
    
    Trans_Rel = bdd.false
    
    for t in transitions:
        t_rel = bdd.true
        
        # A. Pre-conditions (Guard): 
        for p_idx in t["pre"]:
            t_rel = AND(t_rel, x[p_idx])
            
        # B. Post-conditions & Action:
        for i in range(num_places):
            if i in t["pre"] and i not in t["post"]:
                # Consumed: Next state is 0 (NOT y[i])
                t_rel = AND(t_rel, NOT(y[i]))
            elif i in t["post"]:
                # Produced: Next state is 1 (y[i])
                t_rel = AND(t_rel, y[i])
            else:
                # Frame Condition: Unchanged (y[i] <-> x[i])
                # Logic: (x AND y) OR ((NOT x) AND (NOT y))
                term1 = AND(x[i], y[i])
                term2 = AND(NOT(x[i]), NOT(y[i]))
                frame = OR(term1, term2)
                t_rel = AND(t_rel, frame)
        
        # Add this transition to the global relation
        Trans_Rel = OR(Trans_Rel, t_rel)

    # 5. Fixed Point Iteration
    print("  [BDD] Starting Fixed-Point Iteration...")
    
    R = init_bdd
    iterations = 0
    
    # Renaming map: y_i -> x_i
    rename_map = {f"y{i}": f"x{i}" for i in range(num_places)}
    # Variables to existentially quantify
    x_vars = set(f"x{i}" for i in range(num_places))
    
    print("  Iter | BDD Nodes | Reachable States")
    print("  -----+-----------+-----------------")
    
    while True:
        iterations += 1
        
        # --- Symbolic Image Computation ---
        # 1. Conjunction: Valid moves (R AND T)
        next_state_y = AND(R, Trans_Rel)
        
        # 2. Existential Quantification: Abstract away x
        next_state_y = bdd.exist(x_vars, next_state_y)
        
        # 3. Renaming: y -> x
        next_state_x = bdd.let(rename_map, next_state_y)
        
        # --- Convergence Check ---
        # New = Next - R
        new_states = DIFF(next_state_x, R)
        
        if new_states == bdd.false:
            print(f"  Conv | Converged in {iterations} iterations.")
            break
            
        # R = R OR New
        R = OR(R, new_states)
        
        # Metrics
        count = bdd.count(R, nvars=num_places)
        print(f"  {iterations:4d} | {len(bdd):9d} | {count}")

    end_time = time.time()
    final_count = bdd.count(R, nvars=num_places)
    
    print(f"[Symbolic BDD] Done. Total Reachable: {final_count}")
    
    return {
        "bdd_obj": R,
        "bdd_manager": bdd, 
        "count": final_count,
        "nodes": len(bdd),
        "time": end_time - start_time
    }


import pulp # Required for Task 4

# ... (Keep all previous classes: PNMLParser, PetriNetBitmask, symbolic_reachability) ...

# =============================================================================
# TASK 4: DEADLOCK DETECTION (ILP + BDD) - FIXED (KeyError 0 Resolved)
# =============================================================================

# =============================================================================
# TASK 4: DEADLOCK DETECTION (ILP + BDD) - OPTIMIZED (Murata's State Eq)
# =============================================================================

def find_deadlock_ilp_bdd(places, transitions, bdd_obj, bdd_manager, pid_to_idx):
    """
    Finds a deadlock using ILP + BDD, optimized with Murata's State Equation [15].
    
    Improvements:
    1. State Equation (M = M0 + C*sigma): Filters out structurally impossible states.
    2. Minimization Objective: Finds the deadlock reachable with fewest steps.
    3. Robustness: Handles solver 'None' values and BDD boolean mapping.
    """
    print("\n[Task 4] Starting ILP + BDD Deadlock Detection (Optimized)...")
    
    # 1. Setup ILP Problem
    prob = pulp.LpProblem("Deadlock_Finder", pulp.LpMinimize)
    
    # --- Variables ---
    # M_p: Binary variable for each place (0 or 1)
    ilp_vars_M = {}
    for pid, idx in pid_to_idx.items():
        ilp_vars_M[idx] = pulp.LpVariable(f"M_{idx}", cat=pulp.LpBinary)
        
    # sigma_t: Integer variable for firing counts of transitions (>= 0)
    # We use this to enforce the State Equation
    ilp_vars_sigma = []
    for i, t in enumerate(transitions):
        ilp_vars_sigma.append(pulp.LpVariable(f"sigma_{i}", lowBound=0, cat=pulp.LpInteger))

    # --- Constraints ---

    # A. Deadlock Condition (Disablement)
    # For a marking to be dead, NO transition can be enabled.
    # Transition t enabled iff Sum(tokens in Pre) == len(Pre)
    # Disabled iff Sum(tokens in Pre) <= len(Pre) - 1
    constraints_count = 0
    for i, t in enumerate(transitions):
        pre_indices = t['pre']
        if not pre_indices:
            print("  [ILP] Source transition found (always enabled). System cannot deadlock.")
            return None
        
        # Constraint: sum(M_p for p in pre) <= |pre| - 1
        prob += pulp.lpSum([ilp_vars_M[p_idx] for p_idx in pre_indices]) <= len(pre_indices) - 1
        constraints_count += 1

    # B. State Equation (Murata [15]): M = M0 + C * sigma
    # This ensures the marking M is structurally reachable from M0.
    # Equation for each place p: M[p] = M0[p] + Sum(sigma_t * Delta_tp)
    
    # Pre-calculate incidence logic to speed up loop
    # place_incidence[p] = list of (transition_index, +1/-1)
    place_incidence = {idx: [] for idx in pid_to_idx.values()}
    
    for t_idx, t in enumerate(transitions):
        # If t consumes from p: Delta = -1
        for p_idx in t['pre']:
            place_incidence[p_idx].append((t_idx, -1))
        # If t produces into p: Delta = +1
        for p_idx in t['post']:
            place_incidence[p_idx].append((t_idx, 1))
            
    # Add Equation for each place
    for pid, p_idx in pid_to_idx.items():
        # Get Initial Marking M0 for this place
        m0_val = places[pid] 
        
        # Formulate: M[p] - Sum(Delta * sigma) = M0[p]
        delta_expression = pulp.lpSum([val * ilp_vars_sigma[t_idx] for t_idx, val in place_incidence[p_idx]])
        
        prob += (ilp_vars_M[p_idx] - delta_expression) == m0_val
        constraints_count += 1

    # --- Objective Function ---
    # Minimize the total number of firings (sigma). 
    # This prevents unbounded searches in cyclic nets and finds "simple" deadlocks first.
    prob += pulp.lpSum(ilp_vars_sigma)

    print(f"  [ILP] Model built: {len(ilp_vars_M)} places, {len(ilp_vars_sigma)} transitions, {constraints_count} constraints.")

    # 3. Iterative Search
    attempt = 0
    while True:
        attempt += 1
        
        # Solve ILP
        # msg=False suppresses the solver's internal logs
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
        
        if status != pulp.LpStatusOptimal:
            print("  [ILP] No (more) dead markings exist that satisfy the State Equation.")
            return None 
            
        # Extract Candidate Marking M
        candidate_marking = {} 
        for idx, var in ilp_vars_M.items():
            val_raw = pulp.value(var)
            # FIX: Handle Unconstrained variables (None -> 0)
            val = int(val_raw) if val_raw is not None else 0
            candidate_marking[idx] = val
            
        # 4. Check Reachability using BDD
        # FIX: Map 0/1 integers to BDD True/False nodes
        bdd_assignment = {
            f"x{i}": (bdd_manager.true if candidate_marking[i] == 1 else bdd_manager.false)
            for i in candidate_marking
        }

        is_reachable = bdd_manager.let(bdd_assignment, bdd_obj)
        
        if is_reachable == bdd_manager.true:
            print(f"  [Success] Found Deadlock on attempt {attempt}!")
            return candidate_marking
        else:
            # 5. Add "Canonical Cut" to ILP
            # The candidate satisfied the State Equation but was not actually reachable 
            # (State Eq is necessary but not sufficient). We must ban it.
            
            vars_with_1 = [ilp_vars_M[i] for i, val in candidate_marking.items() if val == 1]
            vars_with_0 = [ilp_vars_M[i] for i, val in candidate_marking.items() if val == 0]
            
            # Constraint: Sum(vars that are 1) - Sum(vars that are 0) <= Count(1s) - 1
            prob += (pulp.lpSum(vars_with_1) - pulp.lpSum(vars_with_0)) <= len(vars_with_1) - 1
            
            if attempt % 5 == 0:
                print(f"  [ILP] Attempt {attempt}: Candidate satisfies State Eq but not Reachable (Spurious), retrying...")


# =============================================================================
# TASK 5: OPTIMIZATION OVER REACHABLE MARKINGS
# =============================================================================
import random

def optimize_reachable_marking(places, transitions, bdd_obj, bdd_manager, pid_to_idx, weights):
    """
    Finds a reachable marking M that MAXIMIZES c^T * M.
    
    Algorithm:
    1. Define ILP with State Equation constraints (M = M0 + C*sigma).
    2. Set Objective: Maximize sum(weight_p * M_p).
    3. Iterate:
       - Solve ILP to get 'candidate' (mathematical max).
       - Check if 'candidate' is in BDD (reachable).
       - If YES: Return it (it's guaranteed optimal because ILP solves best-first).
       - If NO: Add cut constraint, Repeat.
    """
    print(f"\n[Task 5] Starting Optimization (Target: Maximize Weighted Sum)...")
    
    # 1. Setup ILP Problem (Maximization)
    prob = pulp.LpProblem("Reachable_Optimization", pulp.LpMaximize)
    
    # --- Variables ---
    # M_p: Binary variable for each place
    ilp_vars_M = {}
    for pid, idx in pid_to_idx.items():
        ilp_vars_M[idx] = pulp.LpVariable(f"M_{idx}", cat=pulp.LpBinary)
        
    # sigma_t: Firing counts (Integer >= 0)
    ilp_vars_sigma = []
    for i, t in enumerate(transitions):
        ilp_vars_sigma.append(pulp.LpVariable(f"sigma_{i}", lowBound=0, cat=pulp.LpInteger))

    # --- Constraints: State Equation (M = M0 + C * sigma) ---
    # Pre-calculate incidence
    place_incidence = {idx: [] for idx in pid_to_idx.values()}
    for t_idx, t in enumerate(transitions):
        for p_idx in t['pre']:
            place_incidence[p_idx].append((t_idx, -1))
        for p_idx in t['post']:
            place_incidence[p_idx].append((t_idx, 1))
            
    # Add Equation for each place
    for pid, p_idx in pid_to_idx.items():
        m0_val = places[pid]
        delta_expression = pulp.lpSum([val * ilp_vars_sigma[t_idx] for t_idx, val in place_incidence[p_idx]])
        prob += (ilp_vars_M[p_idx] - delta_expression) == m0_val

    # --- Objective Function ---
    # Maximize Sum(Weight_p * M_p)
    # weights is a dict {place_id: integer_weight}
    # We map place_id -> index -> variable
    
    obj_terms = []
    for pid, weight in weights.items():
        idx = pid_to_idx[pid]
        obj_terms.append(weight * ilp_vars_M[idx])
        
    prob += pulp.lpSum(obj_terms)
    
    print(f"  [ILP] Objective function set with {len(weights)} weights.")

    # 3. Iterative Search
    attempt = 0
    while True:
        attempt += 1
        
        # Solve
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
        
        if status != pulp.LpStatusOptimal:
            print("  [ILP] No feasible solution found (Search space exhausted).")
            return None, None
            
        # Extract Candidate
        candidate_marking = {} 
        for idx, var in ilp_vars_M.items():
            val_raw = pulp.value(var)
            val = int(val_raw) if val_raw is not None else 0
            candidate_marking[idx] = val
            
        current_score = pulp.value(prob.objective)

        # 4. Check Reachability (Oracle)
        # Map 0/1 to BDD True/False
        bdd_assignment = {
            f"x{i}": (bdd_manager.true if candidate_marking[i] == 1 else bdd_manager.false)
            for i in candidate_marking
        }
        
        is_reachable = bdd_manager.let(bdd_assignment, bdd_obj)
        
        if is_reachable == bdd_manager.true:
            print(f"  [Success] Found Optimal Marking on attempt {attempt}!")
            print(f"  [Result] Score: {current_score}")
            return candidate_marking, current_score
        else:
            # 5. Cut (Unreachable)
            vars_with_1 = [ilp_vars_M[i] for i, val in candidate_marking.items() if val == 1]
            vars_with_0 = [ilp_vars_M[i] for i, val in candidate_marking.items() if val == 0]
            
            # Constraint: Exclude this specific pattern
            prob += (pulp.lpSum(vars_with_1) - pulp.lpSum(vars_with_0)) <= len(vars_with_1) - 1
            
            if attempt % 10 == 0:
                print(f"  [ILP] Attempt {attempt}: Score {current_score} unreachable, digging deeper...")

# =============================================================================
# UPDATE MAIN BLOCK
# =============================================================================
if __name__ == "__main__":
    filename = "samples/net10.pnml" 
    print(f"Reading file: {filename}")
    # parser = PNMLParser(filename).parse()
    # filename = "samples/sample_04.pnml"  # Make sure this file exists
    # print(f"Reading file: {filename}")
    
    # --- TASK 1 execution ---
    parser = PNMLParser(filename).parse()

    print("\n=== TASK 1: Parsed PNML ===")
    print(f"Places ({len(parser.places)}):", parser.places)
    print(f"Transitions ({len(parser.transitions)}):", parser.transitions)
    print(f"Arcs ({len(parser.arcs)}):", len(parser.arcs))

    print("\n=== TASK 1: Validation ===")
    errors = parser.validate()
    if errors:
        for e in errors:
            print("ERROR:", e)
    else:
        print("No validation errors")

    if parser.places:
        # --- TASK 2 execution ---
        print("\n=== TASK 2: Reachability (Bitmask BFS) ===")
        pn_bit = PetriNetBitmask(parser.places, parser.transitions, parser.arcs)
        reachable_masks = pn_bit.reachable_markings_bfs()
        print("Initial mask (int):", pn_bit.initial_mask)
        print("Number of reachable markings:", len(reachable_masks))

        # Print sample
        shown = 0
        print("Sample markings:")
        for mask in list(reachable_masks)[:5]:
            print(" ", pn_bit.mask_to_tuple(mask))
            shown += 1
        if len(reachable_masks) > 5: print(" ...")
    if parser.places:
        # --- PREP DATA ---
        sorted_pids = sorted(parser.places.keys())
        pid_to_idx = {pid: i for i, pid in enumerate(sorted_pids)}
        trans_map = {tid: {'id': tid, 'pre': set(), 'post': set()} for tid in parser.transitions}
        for src, tgt in parser.arcs:
            if src in parser.places and tgt in trans_map:
                trans_map[tgt]['pre'].add(pid_to_idx[src])
            elif src in trans_map and tgt in parser.places:
                trans_map[src]['post'].add(pid_to_idx[tgt])
        structured_transitions = list(trans_map.values())

        try:
            # --- TASK 3 (Prerequisite) ---
            print("\n=== TASK 3: Symbolic Reachability ===")
            sym_result = symbolic_reachability(parser.places, structured_transitions)
            reachable_bdd = sym_result["bdd_obj"]
            manager = sym_result["bdd_manager"]
            print(f"Reachable Count: {sym_result['count']}")

            # --- TASK 4: Deadlock ---
            print("\n=== TASK 4: Deadlock Detection ===")
            deadlock = find_deadlock_ilp_bdd(parser.places, structured_transitions, reachable_bdd, manager, pid_to_idx)
            if deadlock:
                print("Deadlock found:", deadlock)
            else:
                print("No deadlock found.")

            # --- TASK 5: Optimization ---
            print("\n=== TASK 5: Optimization over Reachable Markings ===")
            
            # 1. Generate Random Weights (since file doesn't have them)
            # The assignment says "c assigns integer weights". We simulate this.
            print("  [Setup] Generating random weights for places (-5 to 10)...")
            weights = {}
            print("  Weights map:")
            for pid in parser.places:
                # Assign random weight. 
                # Positive means we WANT tokens here. Negative means AVOID tokens here.
                w = random.randint(-5, 10) 
                weights[pid] = w
                # print small sample
                if len(weights) <= 5: print(f"    {pid}: {w}")
            if len(weights) > 5: print("    ...")

            # 2. Run Optimization
            opt_marking, max_score = optimize_reachable_marking(
                parser.places, 
                structured_transitions, 
                reachable_bdd, 
                manager, 
                pid_to_idx, 
                weights
            )
            
            if opt_marking:
                print(f"\nOPTIMAL MARKING FOUND with Score: {max_score}")
                
                # Convert back to readable names
                idx_to_pid = {v: k for k, v in pid_to_idx.items()}
                
                # Show only places with tokens (for brevity)
                active_places = [idx_to_pid[i] for i, val in opt_marking.items() if val == 1]
                print(f"Active Places in Optimal State: {active_places}")
            else:
                print("No feasible marking found (Model might be inconsistent).")

        except Exception as e:
            import traceback
            traceback.print_exc()
            print("Error:", e)
    else:
        print("Net is empty.")
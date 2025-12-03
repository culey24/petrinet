from dd.bdd import BDD
import time

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
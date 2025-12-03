import pulp

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

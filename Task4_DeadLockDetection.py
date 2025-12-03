import pulp

def find_deadlock_ilp_bdd(places, transitions, bdd_obj, bdd_manager, pid_to_idx):
    """
    Finds a deadlock using ILP + BDD, optimized for 1-safe Petri nets.
    
    Fixed Logic:
    A transition t is DISABLED if:
      (Sum(Input tokens) < |Inputs|)  OR  (Sum(Pure Output tokens) >= 1)
    
    This 'OR' logic is modeled using Big-M constraints with a binary selector variable z.
    """
    print("\n[Task 4] Starting ILP + BDD Deadlock Detection (Fixed for 1-safe)...")
    
    # 1. Setup ILP Problem
    prob = pulp.LpProblem("Deadlock_Finder", pulp.LpMinimize)
    
    # --- Variables ---
    # M_p: Binary variable for each place (0 or 1)
    ilp_vars_M = {}
    for pid, idx in pid_to_idx.items():
        ilp_vars_M[idx] = pulp.LpVariable(f"M_{idx}", cat=pulp.LpBinary)
        
    # sigma_t: Integer variable for firing counts (State Equation)
    ilp_vars_sigma = []
    for i, t in enumerate(transitions):
        ilp_vars_sigma.append(pulp.LpVariable(f"sigma_{i}", lowBound=0, cat=pulp.LpInteger))

    # --- Constraints A: Deadlock Condition (Disable ALL transitions) ---
    # Logic: For each transition t, it must be disabled by Input shortage OR Output blockage.
    # We use a binary variable z_t:
    #   z_t = 0 => Disabled by Input shortage
    #   z_t = 1 => Disabled by Output blockage
    
    constraints_count = 0
    
    for i, t in enumerate(transitions):
        pre_indices = t['pre']
        # Identify "Pure Outputs" (Outputs that are not Inputs) to check for blockage
        pure_post_indices = list(set(t['post']) - set(t['pre']))
        
        len_pre = len(pre_indices)
        
        if len(pure_post_indices) == 0:
            # Case 1: No pure outputs (e.g., sink transition or self-loop only).
            # Can ONLY be disabled by lack of inputs.
            # Constraint: Sum(M_pre) <= |Pre| - 1
            if len_pre > 0:
                prob += pulp.lpSum([ilp_vars_M[p] for p in pre_indices]) <= len_pre - 1
            else:
                # Transition with no inputs and no pure outputs is ALWAYS enabled.
                print("  [ILP] System has an always-enabled transition. No deadlock possible.")
                return None
        else:
            # Case 2: Can be disabled by Input Shortage OR Output Blockage.
            # Introduce binary selector variable z_i
            z = pulp.LpVariable(f"z_disable_{i}", cat=pulp.LpBinary)
            
            # Constraint 2.1: If z=0, enforce Input Shortage
            # Logic: Sum(M_pre) <= (|Pre| - 1) + M * z
            # If z=0: Sum <= |Pre| - 1 (Disabled by input)
            # If z=1: Sum <= Large_Number (Constraint relaxed/ignored)
            # We assume M = |Pre| is large enough.
            if len_pre > 0:
                prob += pulp.lpSum([ilp_vars_M[p] for p in pre_indices]) <= (len_pre - 1) + (len_pre * z)
            
            # Constraint 2.2: If z=1, enforce Output Blockage
            # Logic: Sum(M_post_pure) >= 1 - M * (1 - z)
            # If z=1: Sum >= 1 (Disabled by output full)
            # If z=0: Sum >= Negative_Number (Constraint relaxed/ignored)
            # Since variables are binary, Sum >= z is sufficient.
            prob += pulp.lpSum([ilp_vars_M[p] for p in pure_post_indices]) >= z
            
        constraints_count += 1

    # --- Constraints B: State Equation (Murata) ---
    # M = M0 + C * sigma
    place_incidence = {idx: [] for idx in pid_to_idx.values()}
    for t_idx, t in enumerate(transitions):
        for p_idx in t['pre']:
            place_incidence[p_idx].append((t_idx, -1))
        for p_idx in t['post']:
            place_incidence[p_idx].append((t_idx, 1))
            
    for pid, p_idx in pid_to_idx.items():
        m0_val = places[pid] 
        delta_expression = pulp.lpSum([val * ilp_vars_sigma[t_idx] for t_idx, val in place_incidence[p_idx]])
        prob += (ilp_vars_M[p_idx] - delta_expression) == m0_val
        constraints_count += 1

    # --- Objective: Find simplest deadlock (min firing count) ---
    prob += pulp.lpSum(ilp_vars_sigma)

    print(f"  [ILP] Model built: {len(ilp_vars_M)} places, {constraints_count} constraints.")

    # 3. Iterative Search (Same as before)
    attempt = 0
    while True:
        attempt += 1
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
        
        if status != pulp.LpStatusOptimal:
            print("  [ILP] No (more) dead markings exist that satisfy the State Equation.")
            return None 
            
        # Extract Candidate
        candidate_marking = {} 
        for idx, var in ilp_vars_M.items():
            val_raw = pulp.value(var)
            val = int(val_raw) if val_raw is not None else 0
            candidate_marking[idx] = val
            
        # 4. Check Reachability using BDD
        bdd_assignment = {
            f"x{i}": (bdd_manager.true if candidate_marking[i] == 1 else bdd_manager.false)
            for i in candidate_marking
        }
        is_reachable = bdd_manager.let(bdd_assignment, bdd_obj)
        
        if is_reachable == bdd_manager.true:
            print(f"  [Success] Found Deadlock on attempt {attempt}!")
            return candidate_marking
        else:
            # 5. Spurious Solution Cut
            vars_with_1 = [ilp_vars_M[i] for i, val in candidate_marking.items() if val == 1]
            vars_with_0 = [ilp_vars_M[i] for i, val in candidate_marking.items() if val == 0]
            prob += (pulp.lpSum(vars_with_1) - pulp.lpSum(vars_with_0)) <= len(vars_with_1) - 1
            
            if attempt % 5 == 0:
                print(f"  [ILP] Attempt {attempt}: Spurious candidate (unreachable), retrying...")
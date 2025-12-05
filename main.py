import sys
import random
import traceback
import time
from src.task_1.pnml_parser import PNMLParser
from src.task_2.explicit_bfs import PetriNetBitmask
from src.task_3.symbolic_compute import symbolic_reachability
from src.task_4.deadlock_detection import find_deadlock_ilp_bdd
from src.task_5.optimize import optimize_reachable_marking

filename = "samples/net10.pnml"

if len(sys.argv) > 1:
    filename = sys.argv[1]

print(f"Reading file: {filename}")

parser = PNMLParser(filename).parse()

print("\n=== TASK 1: Parsed PNML ===")
print(f"Places ({len(parser.places)}):", list(parser.places.keys()))
print(f"Transitions ({len(parser.transitions)}):", list(parser.transitions))
print(f"Arcs ({len(parser.arcs)}):", len(parser.arcs))

print("\n=== TASK 1: Validation ===")
errors = parser.validate()
if errors:
    for e in errors:
        print("ERROR:", e)
else:
    print("No validation errors")

if parser.places:
    print("\n=== TASK 2: Reachability (Bitmask BFS) ===")
    start_time = time.time()
    pn_bit = PetriNetBitmask(parser.places, parser.transitions, parser.arcs)
    reachable_masks = pn_bit.reachable_markings_bfs()
    end_time = time.time()
    print(f"Time taken (BFS): {end_time - start_time:.6f} seconds")
    print("Initial mask (int):", pn_bit.initial_mask)
    print("Number of reachable markings:", len(reachable_masks))

    print("Sample markings:")
    shown = 0
    for mask in list(reachable_masks)[:5]:
        print(" ", pn_bit.mask_to_tuple(mask))
        shown += 1
    if len(reachable_masks) > 5: 
        print(" ...")

if parser.places:
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
        print("\n=== TASK 3: Symbolic Reachability ===")
        sym_result = symbolic_reachability(parser.places, structured_transitions)
        
        reachable_bdd = sym_result["bdd_obj"]
        manager = sym_result["bdd_manager"]
        print(f"Reachable Count (BDD): {sym_result['count']}")
        
        if sym_result['count'] == len(reachable_masks):
            print(">> Verification Passed: Symbolic count matches BFS count.")
        else:
            print(f">> Warning: Counts differ! BFS={len(reachable_masks)}, Symbolic={sym_result['count']}")

        print("\n=== TASK 4: Deadlock Detection ===")
        deadlock = find_deadlock_ilp_bdd(
            parser.places, 
            structured_transitions, 
            reachable_bdd, 
            manager, 
            pid_to_idx
        )
        
        if deadlock:
            print("Deadlock found (Marking):", deadlock)
            readable_deadlock = {sorted_pids[k]: v for k, v in deadlock.items() if v > 0}
            print("Deadlock places with tokens:", readable_deadlock)
        else:
            print("No deadlock found.")

        print("\n=== TASK 5: Optimization over Reachable Markings ===")
        
        print("  [Setup] Generating random weights for places (-5 to 10)...")
        weights = {}
        for pid in parser.places:
            w = random.randint(-5, 10) 
            weights[pid] = w
        
        sample_weights = {k: weights[k] for k in list(weights)[:3]}
        print(f"  Sample Weights: {sample_weights} ...")

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
            
            idx_to_pid = {v: k for k, v in pid_to_idx.items()}
            
            active_places = [idx_to_pid[i] for i, val in opt_marking.items() if val == 1]
            print(f"Active Places in Optimal State: {active_places}")
            
            check_score = sum(weights[idx_to_pid[i]] * val for i, val in opt_marking.items())
            print(f"Verified Score calculation: {check_score}")
            
        else:
            print("No feasible marking found (Model might be inconsistent).")

    except Exception as e:
        print("\n[CRITICAL ERROR in Main Logic]")
        traceback.print_exc()
        print("Error details:", e)
else:
    print("Net is empty or parsing failed.")
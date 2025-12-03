import time
from collections import deque
from main import PNMLParser

def build_fast_lookup(places, transitions, arcs):
    lookup = {t: {"in": {}, "out": {}} for t in transitions}
    
    for src, tgt in arcs:
        if src in places and tgt in lookup:
            lookup[tgt]["in"][src] = 1
        elif src in lookup and tgt in places:
            lookup[src]["out"][tgt] = 1
            
    return lookup

def calculate_score(marking, weights):
    total = 0
    for p, tokens in marking.items():
        if tokens > 0:
            total += tokens * weights.get(p, 0)
    return total

def get_next_marking(current_marking, t_in, t_out):
    next_m = current_marking.copy()
    
    for p, w in t_in.items():
        if next_m.get(p, 0) < w:
            return None
        next_m[p] -= w
        
    for p, w in t_out.items():
        next_m[p] = next_m.get(p, 0) + w
        if next_m[p] > 1:
            return None
            
    return next_m

def solve_optimization(initial_marking, transition_lookup, weights):
    start = time.time()
    
    place_ids = sorted(initial_marking.keys())
    
    queue = deque([initial_marking])
    
    visited = set()
    root_sig = tuple(initial_marking[p] for p in place_ids)
    visited.add(root_sig)
    
    best_m = initial_marking
    best_val = calculate_score(initial_marking, weights)
    nodes_count = 0
    
    while queue:
        curr = queue.popleft()
        nodes_count += 1
        
        val = calculate_score(curr, weights)
        if val > best_val:
            best_val = val
            best_m = curr
            
        for t_data in transition_lookup.values():
            nxt = get_next_marking(curr, t_data["in"], t_data["out"])
            
            if nxt:
                sig = tuple(nxt[p] for p in place_ids)
                if sig not in visited:
                    visited.add(sig)
                    queue.append(nxt)
                    
    duration = time.time() - start
    return best_m, best_val, nodes_count, duration

if __name__ == "__main__":
    # Đảm bảo đường dẫn file PNML chính xác
    pnml_file = r"C:\Users\toquo\Documents\Learning material\Mathematical Modeling\MMB_ASSIGNMENT\PetriNetProject\samples\net10.pnml"
    
    try:
        parser = PNMLParser(pnml_file).parse()
        if parser.validate():
            print("Model has errors.")
            exit()
            
        lookup = build_fast_lookup(parser.places, parser.transitions, parser.arcs)
        
        c_vector = {p: 1 for p in parser.places}
        
        result_m, result_val, visited_cnt, exec_time = solve_optimization(
            parser.places, lookup, c_vector
        )
        
        print(f"Optimal Value: {result_val}")
        print(f"Visited States: {visited_cnt}")
        print(f"Time: {exec_time:.5f}s")
        print("Marking:")
        for p in sorted(result_m):
            if result_m[p]:
                print(f"  {p}: {result_m[p]}")

    except Exception as e:
        print(f"Error: {e}")
import random
import os

def generate_large_pnml(filename="samples/large.pnml", num_places=50, num_transitions=40):
    """
    Generates a generic 'Large' 1-safe Petri net for stress testing.
    - num_places: 50 (Theoretical state space 2^50)
    - num_transitions: 40
    - Logic: Random connections, but ensures valid PNML structure.
    """
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    print(f"Generating LARGE model: {num_places} places, {num_transitions} transitions...")
    
    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<pnml><net id="net_large" type="http://www.pnml.org/version-2009/grammar/ptnet">')
    xml.append('<page id="page0">')

    # 1. Places (Nodes p0 ... p49)
    places = [f"p{i}" for i in range(num_places)]
    for p in places:
        # 20% chance of having a token initially (Low density to avoid immediate 1-safe violations)
        tok = 1 if random.random() < 0.2 else 0 
        xml.append(f'<place id="{p}"><initialMarking><text>{tok}</text></initialMarking></place>')

    # 2. Transitions (Nodes t0 ... t39)
    transitions = [f"t{i}" for i in range(num_transitions)]
    for t in transitions:
        xml.append(f'<transition id="{t}"/>')

    # 3. Arcs (Connections)
    # Strategy: Ensure every transition has at least 1 input and 1 output to be active/interesting.
    arc_id = 0
    for t in transitions:
        # Input: Pick 1 or 2 random places as pre-conditions
        # (Using random.sample ensures distinct places)
        num_inputs = random.choice([1, 2])
        inputs = random.sample(places, num_inputs)
        for p in inputs:
            xml.append(f'<arc id="a{arc_id}" source="{p}" target="{t}"/>')
            arc_id += 1
        
        # Output: Pick 1 or 2 random places as post-conditions
        num_outputs = random.choice([1, 2])
        outputs = random.sample(places, num_outputs)
        for p in outputs:
            xml.append(f'<arc id="a{arc_id}" source="{t}" target="{p}"/>')
            arc_id += 1

    xml.append('</page></net></pnml>')

    with open(filename, "w") as f:
        f.write("\n".join(xml))
    print(f"Success! Saved to {filename}")

if __name__ == "__main__":
    generate_large_pnml()
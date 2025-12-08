import random

def generate_pnml(filename, num_places=20, num_trans=15):
    places = [f"p{i}" for i in range(num_places)]
    transitions = [f"t{i}" for i in range(num_trans)]
    
    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<pnml><net id="net1" type="http://www.pnml.org/version-2009/grammar/ptnet">')
    xml.append('<page id="page0">')
    
    # Places
    for p in places:
        tok = 1 if random.random() < 0.2 else 0 # 20% chance of initial token
        xml.append(f'<place id="{p}"><initialMarking><text>{tok}</text></initialMarking></place>')
        
    # Transitions
    for t in transitions:
        xml.append(f'<transition id="{t}"/>')
        
    # Arcs (Random connections to ensure flow)
    arc_id = 0
    for t in transitions:
        # Pre-condition (Place -> Trans)
        src = random.choice(places)
        xml.append(f'<arc id="a{arc_id}" source="{src}" target="{t}"/>'); arc_id += 1
        
        # Post-condition (Trans -> Place)
        tgt = random.choice(places)
        xml.append(f'<arc id="a{arc_id}" source="{t}" target="{tgt}"/>'); arc_id += 1

    xml.append('</page></net></pnml>')
    
    with open(filename, "w") as f:
        f.write("\n".join(xml))
    print(f"Generated {filename}")

if __name__ == "__main__":
    generate_pnml("samples/gen.pnml")
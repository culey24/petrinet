import xml.etree.ElementTree as ET
from collections import deque

class PNMLParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.places = {}
        self.transitions = set()
        self.arcs = []

    def parse(self):
        tree = ET.parse(self.file_path)
        root = tree.getroot()

        net = None
        for child in root:
            if child.tag.endswith('net'):
                net = child
                break
        
        if net is None:
            net = root.find("net") if root.find("net") is not None else root

        def get_tag(elem):
            return elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        for elem in net.iter():
            tag = get_tag(elem)
            
            if tag == 'place':
                pid = elem.attrib.get('id')
                marking = 0
                for child in elem:
                    if get_tag(child) == 'initialMarking':
                        for sub in child:
                            if get_tag(sub) == 'text':
                                try:
                                    marking = int(sub.text)
                                except:
                                    pass
                self.places[pid] = marking

            elif tag == 'transition':
                tid = elem.attrib.get('id')
                self.transitions.add(tid)

            elif tag == 'arc':
                source = elem.attrib.get('source')
                target = elem.attrib.get('target')
                self.arcs.append((source, target))

        return self

    def validate(self):
        errors = []
        for s, t in self.arcs:
            if s not in self.places and s not in self.transitions:
                errors.append(f"Arc source '{s}' does not exist")
            if t not in self.places and t not in self.transitions:
                errors.append(f"Arc target '{t}' does not exist")
        return errors

class PetriNet:
    def __init__(self, places, transitions, arcs):
        self.place_ids = list(places.keys())
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
            i = self.place_ids.index(p)
            if new_m[i] == 0:
                return None 

        for p in self.pre[transition]:
            i = self.place_ids.index(p)
            new_m[i] = 0

        for p in self.post[transition]:
            i = self.place_ids.index(p)
            if new_m[i] == 1:
                return None
            new_m[i] = 1

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

if __name__ == "__main__":
    parser = PNMLParser("samples/net10.pnml").parse()
    
    print("=== TASK 1: Parsed PNML ===")
    print("Places:", parser.places)
    print("Transitions:", parser.transitions)
    
    errors = parser.validate()
    if not errors:
        print("No validation errors")
        
        print("\n=== TASK 2: Reachability (BFS) ===")
        pn = PetriNet(parser.places, parser.transitions, parser.arcs)
        reachable = pn.reachable_markings_bfs()
        print("Total reachable markings:", len(reachable))
    else:
        print("Errors:", errors)
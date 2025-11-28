import xml.etree.ElementTree as ET
from collections import deque

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
        tree = ET.parse(self.file_path)
        root = tree.getroot()

        net = root.find(".//net")

        # ---- Places ----
        for place in net.findall("place"):
            pid = place.attrib["id"]
            marking_el = place.find("./initialMarking/text")
            marking = int(marking_el.text) if marking_el is not None else 0
            self.places[pid] = marking

        # ---- Transitions ----
        for transition in net.findall("transition"):
            tid = transition.attrib["id"]
            self.transitions.add(tid)

        # ---- Arcs ----
        for arc in net.findall("arc"):
            source = arc.attrib["source"]
            target = arc.attrib["target"]
            self.arcs.append((source, target))

        return self

    def validate(self):
        errors = []

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

class PetriNet:
    def __init__(self, places, transitions, arcs):
        self.place_ids = list(places.keys())
        self.initial_marking = tuple(places[p] for p in self.place_ids)

        # build pre/post incidence
        self.pre = {t: set() for t in transitions}
        self.post = {t: set() for t in transitions}

        for s, t in arcs:
            if s in places and t in transitions:
                self.pre[t].add(s)
            elif s in transitions and t in places:
                self.post[s].add(t)

    def fire(self, marking, transition):
        new_m = list(marking)

        # Check enabled
        for p in self.pre[transition]:
            i = self.place_ids.index(p)
            if new_m[i] == 0:
                return None  # not enabled

        # consume tokens
        for p in self.pre[transition]:
            i = self.place_ids.index(p)
            new_m[i] = 0

        # produce tokens
        for p in self.post[transition]:
            i = self.place_ids.index(p)
            if new_m[i] == 1:
                return None  # 1-safe violation
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


# ==========================================================
# Run everything
# ==========================================================

if __name__ == "__main__":
    parser = PNMLParser("samples/net10.pnml").parse()

    print("=== TASK 1: Parsed PNML ===")
    print("Places:", parser.places)
    print("Transitions:", parser.transitions)
    print("Arcs:", parser.arcs)

    print("\n=== TASK 1: Validation ===")
    errors = parser.validate()
    if errors:
        for e in errors:
            print("ERROR:", e)
    else:
        print("No validation errors")

    print("\n=== TASK 2: Reachability (BFS) ===")
    pn = PetriNet(parser.places, parser.transitions, parser.arcs)
    reachable = pn.reachable_markings_bfs()

    print("Initial marking:", pn.initial_marking)
    print("Reachable markings:")
    for m in reachable:
        print(" ", m)

    print("\nTotal reachable markings:", len(reachable))

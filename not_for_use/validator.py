import xml.etree.ElementTree as ET

class PNMLParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.places = {}
        self.transitions = {}
        self.arcs = []

    def parse(self):
        tree = ET.parse(self.file_path)
        root = tree.getroot()

        net = root.find(".//net")

        # Parse places
        for place in net.findall(".//place"):
            pid = place.attrib['id']
            marking_el = place.find(".//initialMarking/text")
            marking = int(marking_el.text) if marking_el is not None else 0
            self.places[pid] = marking

        # Parse transitions
        for transition in net.findall(".//transition"):
            tid = transition.attrib['id']
            self.transitions[tid] = True

        # Parse arcs
        for arc in net.findall(".//arc"):
            source = arc.attrib['source']
            target = arc.attrib['target']
            self.arcs.append((source, target))

        return self


class PetriNetValidator:
    def __init__(self, parser: PNMLParser):
        self.places = parser.places
        self.transitions = parser.transitions
        self.arcs = parser.arcs

    def validate(self):
        errors = []

        # 1. Check for places in arcs
        for source, target in self.arcs:
            if source not in self.places and source not in self.transitions:
                errors.append(f"Undefined source '{source}' in arc ({source} → {target})")
            if target not in self.places and target not in self.transitions:
                errors.append(f"Undefined target '{target}' in arc ({source} → {target})")

        # 2. Check unconnected places and transitions
        used = set()
        for s, t in self.arcs:
            used.add(s)
            used.add(t)

        for p in self.places:
            if p not in used:
                errors.append(f"Place '{p}' is isolated")

        for t in self.transitions:
            if t not in used:
                errors.append(f"Transition '{t}' is isolated")

        # 3. Check arc directions
        for source, target in self.arcs:
            if source in self.places and target in self.places:
                errors.append(f"Invalid arc from place to place: {source} → {target}")
            if source in self.transitions and target in self.transitions:
                errors.append(f"Invalid arc from transition to transition: {source} → {target}")

        return errors


# ---------------------------------------
# Example usage
# ---------------------------------------
if __name__ == "__main__":
    parser = PNMLParser("samples/net10.pnml").parse()
    validator = PetriNetValidator(parser)
    errors = validator.validate()

    if not errors:
        print("No errors found — Petri net is valid!")
    else:
        print("Errors found:")
        for err in errors:
            print(" -", err)

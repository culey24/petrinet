import xml.etree.ElementTree as ET

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
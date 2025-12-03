import xml.etree.ElementTree as ET

class PNMLParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.places = {} 
        self.transitions = set()
        self.arcs = []

    def parse(self):
        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()
        except FileNotFoundError:
            print(f"Error: File '{self.file_path}' not found.")
            return self

        # --- FIX: Strip Namespaces ---
        # The PNML file uses a namespace (xmlns="..."). 
        # We strip it from every tag to make searching easy.
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
        # -----------------------------

        net = root.find("net")
        if net is None:
            print("Error: Could not find <net> element. Check XML structure.")
            return self

        # ---- Places ----
        for place in net.findall(".//place"):
            pid = place.attrib["id"]
            # Handle potential missing initialMarking
            marking_el = place.find(".//initialMarking/text") 
            if marking_el is not None and marking_el.text:
                marking = int(marking_el.text)
            else:
                marking = 0
            self.places[pid] = marking

        # ---- Transitions ----
        for transition in net.findall(".//transition"):
            tid = transition.attrib["id"]
            self.transitions.add(tid)

        # ---- Arcs ----
        for arc in net.findall(".//arc"):
            source = arc.attrib["source"]
            target = arc.attrib["target"]
            self.arcs.append((source, target))

        return self

    def validate(self):
        errors = []
        if not self.places and not self.transitions:
            errors.append("Net is empty (Parsing failed or empty file).")
            return errors

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

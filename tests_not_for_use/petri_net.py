from pathlib import Path
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from typing import Dict, List, Tuple, Set


class PetriNet:
    def __init__(self):
        self.places: Dict[str, str] = {}
        self.transitions: Dict[str, str] = {}

        # stores (source, target, weight)
        self.arcs: List[Tuple[str, str, int]] = []

        # initial tokens MULTIPLICITY
        self.initial_marking: Dict[str, int] = {}

        # weighted pre/post relations:
        # pre[t][p] = w, post[t][p] = w
        self.pre: Dict[str, Dict[str, int]] = defaultdict(dict)
        self.post: Dict[str, Dict[str, int]] = defaultdict(dict)

    @staticmethod
    def _local_name(tag: str) -> str:
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    # -----------------------
    # PNML PARSER (fixed)
    # -----------------------
    @classmethod
    def from_pnml(cls, path: str) -> "PetriNet":
        net = cls()

        tree = ET.parse(path)
        root = tree.getroot()

        for elem in root.iter():
            lname = cls._local_name(elem.tag).lower()

            # -------- places --------
            if lname == "place":
                pid = elem.attrib.get("id")
                name = None

                for c in elem:
                    if cls._local_name(c.tag).lower() == "name":
                        for t in c.iter():
                            if cls._local_name(t.tag).lower() == "text":
                                name = (t.text or "").strip()

                initial = 0
                for c in elem:
                    if cls._local_name(c.tag).lower() in ("initialmarking", "initialmark"):
                        for t in c.iter():
                            if cls._local_name(t.tag).lower() in ("text", "value"):
                                try:
                                    initial = int(float(t.text.strip()))
                                except:
                                    initial = 0

                net.places[pid] = name or pid
                net.initial_marking[pid] = initial

            # -------- transitions --------
            elif lname == "transition":
                tid = elem.attrib.get("id")
                name = None
                for c in elem:
                    if cls._local_name(c.tag).lower() == "name":
                        for t in c.iter():
                            if cls._local_name(t.tag).lower() == "text":
                                name = (t.text or "").strip()
                net.transitions[tid] = name or tid

            # -------- arcs (now with weights) --------
            elif lname == "arc":
                src = elem.attrib.get("source")
                tgt = elem.attrib.get("target")

                weight = 1  # default
                for c in elem:
                    if cls._local_name(c.tag).lower() == "inscription":
                        for t in c.iter():
                            if cls._local_name(t.tag).lower() in ("text", "value"):
                                try:
                                    weight = int(float(t.text.strip()))
                                except:
                                    weight = 1

                net.arcs.append((src, tgt, weight))

        # ---------------------
        # Build weighted pre/post
        # ---------------------
        for src, tgt, w in net.arcs:
            if src in net.places and tgt in net.transitions:
                net.pre[tgt][src] = w
            elif src in net.transitions and tgt in net.places:
                net.post[src][tgt] = w

        return net

    # -------------------------
    # VALIDATION
    # -------------------------
    def validate(self):
        msgs = []
        valid = True
        all_nodes = set(self.places) | set(self.transitions)

        for src, tgt, w in self.arcs:
            if src not in all_nodes:
                msgs.append(f"Arc source {src} does not exist.")
                valid = False
            if tgt not in all_nodes:
                msgs.append(f"Arc target {tgt} does not exist.")
                valid = False
            if w <= 0:
                msgs.append(f"Arc {src}->{tgt} has non-positive weight {w}.")
                valid = False
            if src in self.places and tgt in self.places:
                msgs.append(f"Invalid place-to-place arc {src}->{tgt}")
                valid = False
            if src in self.transitions and tgt in self.transitions:
                msgs.append(f"Invalid transition-to-transition arc {src}->{tgt}")
                valid = False

        return valid, msgs

    # ------------------------
    # ORDERING & MARKINGS
    # ------------------------
    def places_order(self) -> List[str]:
        return sorted(self.places.keys())

    def initial_marking_vector(self):
        order = self.places_order()
        return tuple(self.initial_marking.get(p, 0) for p in order)

    # ------------------------
    # ENABLED / FIRING
    # ------------------------
    def enabled_transitions(self, marking):
        order = self.places_order()
        pos = {p: i for i, p in enumerate(order)}

        enabled = []
        for t in self.transitions:
            ok = True
            for p, w in self.pre.get(t, {}).items():
                if marking[pos[p]] < w:
                    ok = False
                    break
            if ok:
                enabled.append(t)
        return enabled

    def fire(self, marking, tid):
        order = self.places_order()
        pos = {p: i for i, p in enumerate(order)}

        newm = list(marking)

        # subtract pre weights
        for p, w in self.pre.get(tid, {}).items():
            newm[pos[p]] -= w

        # add post weights
        for p, w in self.post.get(tid, {}).items():
            newm[pos[p]] += w

        return tuple(newm)

    # ------------------------
    # BFS REACHABILITY
    # ------------------------
    def reachable_markings_bfs(self):
        start = self.initial_marking_vector()
        queue = deque([start])
        visited = {start}

        while queue:
            m = queue.popleft()
            for t in self.enabled_transitions(m):
                newm = self.fire(m, t)
                if newm not in visited:
                    visited.add(newm)
                    queue.append(newm)

        return visited

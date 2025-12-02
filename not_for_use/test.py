import os
from not_for_use.petri_net import PetriNet

for f in os.listdir("samples"):
    if f.endswith(".pnml"):
        print("\n====================")
        print("Testing:", f)
        print("====================")

        net = PetriNet.from_pnml("samples/" + f)
        valid, msgs = net.validate()

        print("Valid:", valid)
        for msg in msgs:
            print("-", msg)

        print("Initial:", net.initial_marking_vector())
        print("Reachable:", net.reachable_markings_bfs())

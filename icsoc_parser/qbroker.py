import os
import json

COMPUTERS = "machines"

class QBroker:

    def __init__(self, policy, id=0):
        self.policy = policy
        self.id = id

    def __str__(self):
        return "QBroker: id={0}, policy={1}".format(self.id, self.policy)
    
    def __repr__(self):
        return self.__str__()
    
    def __eq__(self, other):
        return self.id == other.id and self.policy == other.policy
    
    def get_computers(self):
        computers = []
        for c in os.listdir(COMPUTERS):
            if c.endswith(".json"):
                with open(os.path.join(COMPUTERS, c)) as f:
                    computer = json.load(f)
                    computers.append(computer)

        return computers

    
    def dispatch(self, request):
        computers = self.get_computers()
        return self.policy(computers, request)
    
    def run(self, request):

        distribution = {}

        #print("Running request: {} on {}".format(request, self))
        computers = self.dispatch(request)
        for c in computers:
            print("Sending {} shots for circuit {} to {}".format(c[2], c[1], c[0]))

        return distribution

if __name__ == "__main__":

    def policy(computers, request):
        res = []
        shots_per_computer = request["shots"] // len(computers)
        for c in computers:
            res.append((c["name"],shots_per_computer))
        last = request["shots"] % len(computers)
        if last > 0:
            res.pop()
            res.append((computers[-1]["name"],shots_per_computer+last))
        return res
    
    qb = QBroker(policy)
    print(qb)
    print(qb.run({"shots":2001}))
    
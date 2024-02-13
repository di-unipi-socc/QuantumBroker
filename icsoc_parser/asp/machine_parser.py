import os
import json

MULT_CONST = 1 #TODO: REMOVE THIS CONSTANT

def search(machine, path):
    if not path:
        return machine
    if isinstance(machine, dict):
        return search(machine.get(path[0]), path[1:])
    if isinstance(machine, list):
        return [search(m, path) for m in machine]
    return None

def inverted_dict(d):
    inv = {}
    for k, v in d.items():
        inv[v] = k
    return inv

def parse_formula(formula, machine, inverted):
    if formula is None:
        return None
    if isinstance(formula, list):
        return [parse_formula(f, machine, inverted) for f in formula]
    if isinstance(formula, dict):
        return {k: parse_formula(v, machine, inverted) for k, v in formula.items()}
    if isinstance(formula, str):
        if formula in inverted:
            return inverted[formula]
        else:
            s = search(machine, formula.split("."))
            if s is not None:
                return s
            return formula
    else:
        return formula

def project(machine, machines_map):
    projected_machine = {}
    inverted = inverted_dict(machines_map)
    for k, v in machines_map.items():
        value = search(machine, v.split("."))
        if value is not None:
            if isinstance(value, dict) and "@" in value:
                value = parse_formula(value["@"], machine, inverted)
            projected_machine[k] = value
    return projected_machine

def formula_to_ASP(f):
    asp = ""
    attrs = []
    mac_attrs = []
    if isinstance(f, dict):
        key = list(f.keys())[0]
        for el in f[key]:
            formula, attr, mac_attr = formula_to_ASP(el)
            attrs += attr
            mac_attrs += mac_attr
            asp += "("+formula+") " + key + " "
        asp = asp[:-len(key)-2]
    else:
        if isinstance(f, str) and f.startswith("#"): #TODO: remove attrs
            asp += "{}".format(f[1:])
        elif isinstance(f, str):
            asp += "{}".format(f).capitalize()
            mac_attrs.append(f)
        else:
            if isinstance(f, float) or isinstance(f, int):
                pass
                #f = int(f*MULT_CONST) #ATTENTION: CONSTANT FOR AVOIDING FLOATING POINT
            asp += str(f)
    return asp, attrs, mac_attrs

def to_ASP(machine):
    asp = ""
    key = machine["key"].lower()
    for k, v in machine.items():
        if isinstance(v, dict):
            formula, attrs, mac_attrs = formula_to_ASP(v)
            asp += "{}({}, Res) :- ".format(k, key)
            for attr in attrs:
                asp += "{}({}), ".format(attr.lower(), attr.capitalize())
            for attr in mac_attrs:
                asp += "{}({}, {}), ".format(attr.lower(), key, attr.capitalize())
            asp += "Res = {}.\n".format(formula).replace("'", "")
        elif isinstance(v, str) and v.startswith("$"): #ATTENTION: if the string in the machine file starts with a $ it is intepreted as a ASP formula
            asp += "{}({}, Res) :- ".format(k, key)
            asp += "Res = {}.\n".format(v[1:])
        elif k == "key":
            asp += "machine({}).\n".format(key)
        elif isinstance(v, list):
            for el in v:
                if isinstance(el, float) or isinstance(el, int):
                    pass
                    #el = int(el*MULT_CONST) #ATTENTION: CONSTANT FOR AVOIDING FLOATING POINT
                asp += ("{}({}, {}).\n".format(k, key, el).replace("'", "").lower()).replace(" ", "_").replace(",_", ", ")
        else:
            if isinstance(v, float) or isinstance(v, int):
                pass
                #v = int(v*MULT_CONST) #ATTENTION: CONSTANT FOR AVOIDING FLOATING POINT
            asp += ("{}({}, {}).\n".format(k, key, v).replace("'", "").lower()).replace(" ", "_").replace(",_", ", ")
    return asp

def parse_machines(machines, machines_map):
    projected_machines = []

    for m in machines:
        projected_machines.append(project(m, machines_map))

    parsed_machines = []

    for m in projected_machines:
        asp = to_ASP(m)
        parsed_machines.append(asp)

    return parsed_machines

def test():
    MAP = "machines-map.json"
    MACHINES = "machines"
    OUTPUT = "machines.lp"
    
    print("Parsing machines...")

    with open(MAP) as f:
        machines_map = json.load(f)

    machines = []

    for m in os.listdir(MACHINES):
        if m.endswith(".json"):
            with open(os.path.join(MACHINES, m)) as f:
                machine = json.load(f)
                machines.append(machine)

    parsed_machines = parse_machines(machines, machines_map)

    with open(OUTPUT, "w+") as f:
        f.write("\n".join(parsed_machines))
        #print("\n".join(parsed_machines))

if __name__ == "__main__":
    test()
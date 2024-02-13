import json

MULT_CONST = 1 #TODO: REMOVE THIS CONSTANT

def search(request, path):
    if not path:
        return request
    if isinstance(request, dict):
        return search(request.get(path[0]), path[1:])
    if isinstance(request, list):
        return [search(m, path) for m in request]
    return None

# def project(request, request_map):
#     projected_request = {}
#     for k, v in request_map.items():
#         value = search(request, v.split("."))
#         if value is not None:
#             projected_request[k] = value
#     return projected_request
    

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
        if isinstance(f, str) and f.startswith("machine."):
            asp += "{}".format(f[8:]).capitalize()
            mac_attrs.append(f[8:])
        elif isinstance(f, str):
            asp += "{}".format(f).capitalize()
            attrs.append(f)
        else:
            asp += str(f)
    return asp, attrs, mac_attrs

def to_ASP(request):
    asp = ""
    metrics = []
    machine_metrics = []
    for k, v in request.items():
        if k == "kb":
            for el in v:
                if el.endswith("."):
                    asp += el
                else:
                    asp += el + "."
                asp += "\n"
        elif k == "constraints": #TODO: add dispatch. here
            for c in v:
                if isinstance(c, dict):
                    if "op" in c:
                        if c["op"] == "diff":
                            op = "=="
                        elif c["op"] == "eq":
                            op = "!="
                        elif c["op"] == "gt":
                            op = "<"
                        elif c["op"] == "lt":
                            op = ">"
                            
                        asp += ":- compatible(M, C), "


                        if type(c["value"]) != str and c["target"].startswith("machine."):
                            asp += "{}(M, {}), {} {} {}.\n".format(c["target"][8:].lower(), c["target"][8:].capitalize(), c["target"][8:].capitalize(), op, c["value"]).replace("'", "")
                        elif type(c["value"]) != str and (not c["target"].startswith("machine.")):
                            asp += "{}({}), {} {} {}.\n".format(c["target"].lower(), c["target"].capitalize(), c["target"].capitalize(), op, c["value"]).replace("'", "")

                        #TODO: check all the cases
                        elif c["target"].startswith("machine.") and (not c["value"].startswith("machine.")):
                            c["target"] = c["target"][8:]
                            asp += "{}(M, {}), {} {} {}.\n".format(c["target"].lower(), c["target"].capitalize(), c["target"].capitalize(), op, c["value"]).replace("'", "")
                        elif c["value"].startswith("machine.") and (not c["target"].startswith("machine.")):
                            asp += "{}(M, {}), {} {} {}.\n".format(c["value"][8:].lower(), c["value"][8:].capitalize(), c["target"].capitalize(), op, c["value"][8:]).replace("'", "")
                        elif c["value"].startswith("machine.") and c["target"].startswith("machine."):
                            asp += "{}(M, {}), {}(M, {}), {} {} {}.\n".format(c["value"][8:].lower(), c["value"][8:].capitalize(), c["target"][8:].lower(), c["target"][8:].capitalize(), c["target"][8:].capitalize(), op, c["value"][8:]).replace("'", "")                        
                        elif c["value"].startswith("metric.") and (not c["target"].startswith("machine.")):
                            asp += "{}({}), {}({}), {} {} {}.\n".format(c["target"].lower(), c["target"].capitalize(), c["value"][7:].lower(), c["value"][7:].capitalize(), c["target"].capitalize(), op, c["value"][7:].capitalize()).replace("'", "")
                        elif c["value"].startswith("metric.") and c["target"].startswith("machine."):
                            asp += "{}(M, {}), {}({}), {}(M, {}), {} {} {}.\n".format(c["target"][8:].lower(), c["target"][8:].capitalize(), c["value"][7:].lower(), c["value"][7:].capitalize(), c["target"][8:].lower(), c["target"][8:].capitalize(), c["target"][8:].capitalize(), op, c["value"][7:].capitalize()).replace("'", "")
                        else:
                            asp += "{}({}), {} {} {}.\n".format(c["target"].lower(), c["target"].capitalize(), c["target"].capitalize(), op, c["value"]).replace("'", "")
                elif isinstance(c, list): #ATTENTION: if list the constraint is simply the concatenation of the ASP elements
                    asp += ":- compatible(M), "+" ".join(c)+".\n"

                if "default" in c: #default is true by default
                    if not c["default"]:
                        if c["target"].startswith("machine."):
                            asp += ":- compatible(M), not {}(M, _).\n".format(c["target"][8:].lower())
                        else:
                            asp += ":- not {}(_).\n".format(c["target"].lower())
        elif k == "metrics":
            for m in v:
                key = m["key"]
                metrics.append(key)
                val = m["value"]

                if key.startswith("machine."):
                    machine_metrics.append(key[8:])
                    metrics.pop()
                    key = key[8:]
                    asp += "{}(M, {}) :- ".format(key.lower(), key.capitalize())
                elif key.startswith("dispatch."):
                    machine_metrics.append(key[8:])
                    metrics.pop()
                    key = key[9:]
                    asp += "{}(M, C, S, {}) :- ".format(key.lower(), key.capitalize())
                else:
                    asp += "{}({}) :- ".format(key.lower(), key.capitalize())


                if isinstance(val, dict):
                    op = ""
                    if "count" in val:
                        op = "count"
                    elif "sum" in val:
                        op = "sum"
                    elif "min" in val:
                        op = "min"
                    elif "max" in val:
                        op = "max"
                    elif "avg" in val:
                        op = "avg"
                    elif "is" in val:
                        op = "is"

                    if op == "":
                        formula, attrs, mac_attrs = formula_to_ASP(val)
                        for attr in attrs:
                            asp += "{}({}), ".format(attr.lower(), attr.capitalize())
                        for attr in mac_attrs:
                            asp += "{}(M, {}), ".format(attr.lower(), attr.capitalize())
                        asp += "{} = {}.\n".format(key.capitalize(), formula).replace("'", "")
                    else:
                        such_as = ""
                        if "such_as" in val:
                            such_as = ", ".join(val["such_as"])
                        if op == "is":
                            asp += "{} = {}, {} = {}.\n".format(key.capitalize(), (", ".join(val[op])), (", ".join(val[op])), such_as)
                        else:
                            asp += "{} = #{}{{ {} : {} }}.\n".format(key.capitalize(), op, (", ".join(val[op])), such_as)
                elif isinstance(val, list): #ATTENTION: if list the metric is simply the concatenation of the ASP elements
                    asp += ", ".join(val)+".\n"
        elif k == "optimise":
            i = len(v)
            for m in v:
                if m.startswith("-"):
                    m = m[1:]
                    asp += "#maximize"
                else:
                    asp += "#minimize"

                asp += "{{{}@{} : {}({})}}.\n".format(m.capitalize(), i, m, m.capitalize())
                i -= 1
        elif k == "penalties" and len(v) != 0:
            asp += "score(Score) :- "
            total = []
            for p in v:
                if isinstance(p, dict) and "@" in p:
                    formula, attrs, mac_attrs = formula_to_ASP(p["@"])
                    for attr in attrs:
                        asp += "{}({}), ".format(attr.lower(), attr.capitalize())
                    for attr in mac_attrs:
                        asp += "{}(M, {}), ".format(attr.lower(), attr.capitalize())
                    total.append("({})".format(formula))
            asp += "Score = {}.\n".format(" + ".join(total)).replace("'", "")

        else:
            if k == "shots":
                k = "total_shots"
            asp += "{}({}).\n".format(k.lower(), v).replace("'", "").lower()

    # if "penalties" not in request or len(request["penalties"]) == 0:
    #     asp += "score(0).\n"

    for m in metrics:
        asp += "#show {}/1.\n".format(m.lower())
    for m in machine_metrics:
        #asp += "#show {}/2.\n".format(m.lower())
        pass
    return asp


def parse_request(request):
    #projected_request = project(request)
    projected_request = {}

    for k,v in request.items():
        if k not in projected_request and k != "circuit" and not k.startswith("@"):
            projected_request[k] = v

    if "optimise" in projected_request:
        projected_request["optimise"] = projected_request["optimise"] # + ["score"]

    if "granularity" not in projected_request:
        projected_request["granularity"] = 1

    if "max_cost" not in projected_request:
        projected_request["max_cost"] = 99999999

    if "max_time" not in projected_request:
        projected_request["max_time"] = 99999999

    return to_ASP(projected_request)

def test(REQUEST="request.json"):
    OUTPUT = "request.lp"
    DEFAULT = "default.lp"
    
    print("Parsing request {}...".format(REQUEST))

    with open(REQUEST) as f:
        request = json.load(f)

    parsed_request = parse_request(request)

    with open(DEFAULT) as f:
        default = f.read()

    parsed_request = default + "\n\n" + parsed_request

    with open(OUTPUT, "w+") as f:
        f.write(parsed_request)
        #print(parsed_request)

if __name__ == "__main__":
    test()
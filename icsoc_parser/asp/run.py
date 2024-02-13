import json
import time
from datetime import datetime

from machine_parser import test as machine_test
from request_parser import test as request_test

from clyngor import solve

REQUEST = "request-scenario.json"

if __name__ == "__main__":
    with open(REQUEST) as f:
        original_request = json.load(f)

    machine_test()
    request_test(REQUEST)

    with open("request.lp") as f:
        request = f.read()

    with open("machines.lp") as f:
        machines = f.read()

    with open("program.lp", "w+") as f:
        f.write(machines)
        f.write("\n")
        f.write(request)

    print("Solving...")

    start = time.time()
    print("Start time: {}".format(datetime.fromtimestamp(start)))

    if "@time_limit" in original_request:
        answers = solve('program.lp', options=["--time-limit={}".format(original_request["@time_limit"])])
    else:
        answers = solve('program.lp') 
    answer = None
    for answer in answers.by_predicate:
        print(answer)
    end = time.time()
    print("End time: {}".format(datetime.fromtimestamp(end)))
    print(answer)

    print("Time elapsed: {}".format(end - start))
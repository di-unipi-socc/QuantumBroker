import json
import time
import random

from clyngor import solve

from pytket.circuit import OpType

from qiskit.circuit import QuantumCircuit
from qiskit_ibm_provider import IBMProvider

from components.dispatcher import Dispatcher

from components.qbroker import brokering as QuantumBroker, process_partial_distributions
from components.translator import Translator
from components.utils.logger import *

from components.utils.utils import ThreadWithReturnValue as Thread

from threading import Semaphore
circuits_semaphore = Semaphore(1)

BUILDING_BLOCKS = "../.caches/.building_blocks.json"

t = Translator()

def asp_solver(program, optmode=None, parallel_mode=None, project=None, time_limit=None):
    clasp_options = ""
    
    if optmode is not None:
        clasp_options += f"--opt-mode={optmode} "
    if parallel_mode is not None:
        clasp_options += f"--parallel-mode={parallel_mode} "
    if project is not None and project:
        clasp_options += "--project "
    if time_limit is not None:
        clasp_options += f"--time-limit={time_limit} "
    
    answers = solve(program, options=clasp_options, stats=True)
    log_info("ASP Solver run as: `{}`".format(answers.command))
    for answerset in answers.with_optimality.by_predicate:
        yield answerset


def run_asp(file, all_answers=False, optmode=None, parallel_mode=None, project=None, time_limit=None):
    log_info("Running ASP...")
    
    if all_answers:
        answer = []
    else:
        answer = None
    
    start = time.time()

    #clasp_options = '--opt-mode=optN', '--parallel-mode=8', '--project', '--time-limit=900'
    answers = asp_solver(file, optmode, parallel_mode, project, time_limit)
    
    loaded = []
    foundOpt = False
    
    for ans,metrics,optimality in answers:
        loaded.append((metrics,ans,optimality))
        
        if all_answers:
            continue
        else:
            if optimality:
                answer = ans
                foundOpt = True
                break
    
    end = time.time()
    
    if all_answers:
        answer = loaded
    else:
        if not foundOpt:
            log_info("No optimal solution found, printing best solution...")
            loaded = sorted(loaded)
            answer = loaded[0][1]
        else:
            log_info("Optimal solution found!")
            
    log_info("ASP finished.")

    log_debug("Time elapsed: {}".format(end - start))
    
    with open(file, "r") as f:
        program = f.read()
    
    # perf_store("asp", "program", program)
    # perf_store("asp", "time", end - start)
    # perf_store("asp", "answers", loaded)
    # perf_store("asp", "optimal", foundOpt)
    # perf_store("asp", "optimal_answer", answer)
    # perf_store("asp", "settings", {
    #     "optmode": optmode,
    #     "parallel_mode": parallel_mode,
    #     "project": project,
    #     "time_limit": time_limit
    # })
    # perf_store("asp", "all_answers?", all_answers)
    
    return answer

def get_circuit_execution_time(circuit):
    try:
        t = Translator()
        circuit_ = t.translate(circuit["circuit"], QuantumCircuit)
    except:
        return None
    
    b = IBMProvider().get_backend("simulator_stabilizer")
    
    for _ in range(3):
        try:
            circuits_semaphore.acquire()
            time.sleep(5)
            time.sleep(random.randint(0, 5))
            
            job = b.run(circuit_)
            while job.status().name != "DONE":
                time.sleep(1)
            circuits_semaphore.release()
            
            return job.result().time_taken
        except:
            try:
                circuits_semaphore.release()
            except:
                pass
            time.sleep(30)
            
    return None

def parse_circuit(circuit_id, circuit):
    
    def parse_execution_time(circuit):
        execution_time = get_circuit_execution_time(circuit)
        if execution_time is not None:
            return f"circuit_execution_time({circuit_id}, \"{execution_time}\").\n"
        else:
            return f"circuit_execution_time({circuit_id}, \"1000\").\n"
        
    try:
        tket_circuit = t.translate(circuit["circuit"], "tket")
    except: 
        return ""
        
    
    thread = Thread(target=parse_execution_time, args=(circuit,))
    thread.start()
    
    text = ""
    
    text += f"circuit({circuit_id}, {circuit['provider']}, {circuit['backend'].lower()}, {circuit['compiler']}).\n"
    
    text += f"circuit_depth({circuit_id}, {tket_circuit.depth()}).\n"
    text += f"circuit_depth2q({circuit_id}, {tket_circuit.depth_2q()}).\n"
    
    text += f"circuit_width({circuit_id}, {tket_circuit.n_qubits}).\n"
    
    text += f"circuit_bits({circuit_id}, {tket_circuit.n_bits}).\n"
    text += f"circuit_gates({circuit_id}, {tket_circuit.n_gates}).\n"
    text += f"circuit_1q_gates({circuit_id}, {tket_circuit.n_1qb_gates()}).\n"
    text += f"circuit_2q_gates({circuit_id}, {tket_circuit.n_2qb_gates()}).\n"
    for i in range(3, 9):
        text += f"circuit_nq_gates({circuit_id}, {i}, {tket_circuit.n_nqb_gates(i)}).\n"
        
    text += f"circuit_spam_gates({circuit_id}, {tket_circuit.n_gates_of_type(OpType.Measure) + tket_circuit.n_gates_of_type(OpType.Reset)}).\n"
    
    text += thread.join()
    
    text += "\n\n"
    
    return text

def parse_repository(repository):
    log_info("Parsing repository...")
    
    circuits = "\n"
    
    compilers = []
    
    threads = {}
    for circuit_id, circuit in repository.items():
        threads[circuit_id] = Thread(target=parse_circuit, args=(circuit_id, circuit))  
        threads[circuit_id].start()      
        compilers.append(circuit['compiler'])
        
    compilers = list(set(compilers))
    for compiler in compilers:
        circuits += f"compiler({compiler}).\n"
        
    circuits += "\n\n\n"
        
    for circuit_id, thread in threads.items():
        circuits += thread.join()
    
    log_info("Repository parsed.")
    
    return circuits

def parse_backend(backend_id, provider, backend):
    backend_id = backend_id.lower()
    infra = ""
    infra += f"backend({provider}, {backend_id}).\n"
    if "simulator" in backend and backend["simulator"]:
        infra += f"backend_technology({provider}, {backend_id}, simulator).\n"
    elif "technology" in backend:
        infra += f"backend_technology({provider}, {backend_id}, {backend['technology']}).\n"
    else:
        infra += f"backend_technology({provider}, {backend_id}, not_available).\n"
        
    if "waiting_time" in backend:
        infra += f"backend_waiting_time({provider}, {backend_id}, {backend['waiting_time']}).\n"
    else:
        infra += f"backend_waiting_time({provider}, {backend_id}, 100).\n"
        
    if "max_shots" in backend:
        infra += f"backend_max_shots({provider}, {backend_id}, {backend['max_shots']}).\n"
    else:
        infra += f"backend_max_shots({provider}, {backend_id}, 300).\n"
    
    if "max_circuits" in backend:
        infra += f"backend_max_circuits({provider}, {backend_id}, {backend['max_circuits']}).\n"
    else:
        infra += f"backend_max_circuits({provider}, {backend_id}, 1).\n"
    
    if "pending_jobs" in backend:
        infra += f"backend_pending_jobs({provider}, {backend_id}, {backend['pending_jobs']}).\n"
    else:
        infra += f"backend_pending_jobs({provider}, {backend_id}, 0).\n"
        
    if "is_free" in backend:
        is_free = "true" if backend["is_free"] else "false"
        infra += f"backend_is_free({provider}, {backend_id}, {is_free}).\n"
    else:
        infra += f"backend_is_free({provider}, {backend_id}, true).\n"
        
    if "cost" in backend:
        pricing = json.dumps(backend['cost']).replace('\"', '\'')
        infra += f"backend_pricing({provider}, {backend_id}, \"{pricing}\").\n"
    else:   
        infra += f"backend_pricing({provider}, {backend_id}, \"[]\").\n"
        
    
    infra += "\n"
    
    return infra

def parse_backends(backends_info):
    log_info("Parsing backends...")
    
    infra = "\n\n\n\n"
    
    threads = {}
    for provider, backends in backends_info.items():
        for backend_id, backend in backends.items():
            if backend is not None:
                threads[backend_id] = Thread(target=parse_backend, args=(backend_id, provider, backend))
                threads[backend_id].start()
                
    for backend_id, thread in threads.items():
        infra += thread.join()
        
    infra += "\n"
    
    log_info("Backends parsed.")
    
    return infra

def parse_requirements(requirements):
    log_info("Parsing requirements...")
    
    reqs = "\n\n\n\n"
    
    if "constants" not in requirements:
        requirements["constants"] = {}
        
    if "total_shots" not in requirements["constants"]:
        requirements["constants"]["total_shots"] = 1024
    if "granularity" not in requirements["constants"]:
        requirements["constants"]["granularity"] = 100
    if "max_cost" not in requirements["constants"]:
        requirements["constants"]["max_cost"] = "inf"
    if "max_time" not in requirements["constants"]:
        requirements["constants"]["max_time"] = "inf"
    
    if "constants" in requirements:
        for k, v in requirements["constants"].items():
            reqs += f"{k}({v}).\n"
        reqs += "\n"
        
    if "objectives" in requirements:
        size = len(requirements["objectives"])
        for k in requirements["objectives"]:
            if k.startswith("-"):
                reqs += f"#minimize{{V@{size} : {k[1:]}(V)}}.\n"
            else:
                reqs += f"#maximize{{V@{size} : {k}(V)}}.\n"
            size -= 1
        reqs += "\n"
        
    building_blocks = {"metrics": {}, "constraints": {}}
    try:
        with open(BUILDING_BLOCKS, "r") as f:
            building_blocks = json.load(f)
    except:
        pass
    
    
    if "metrics" in requirements:
        for k, v in requirements["metrics"].items():
            if k == "@":
                for m in v:
                    if m in building_blocks["metrics"]:
                        reqs += building_blocks["metrics"][m] + "\n"
            else:
                reqs += v + "\n"
                with open(BUILDING_BLOCKS, "w") as f:
                    building_blocks["metrics"][k] = v
                    json.dump(building_blocks, f)
        reqs += "\n"
        
    if "constraints" in requirements:
        for k, v in requirements["constraints"].items():
            if k == "@":
                for m in v:
                    if m in building_blocks["constraints"]:
                        reqs += building_blocks["constraints"][m] + "\n"
            else:
                reqs += v + "\n"
                with open(BUILDING_BLOCKS, "w") as f:
                    building_blocks["constraints"][k] = v
                    json.dump(building_blocks, f)
        reqs += "\n"
    
    log_info("Requirements parsed.")
    
    return reqs

def parse_answer(answer, repository):
    if "dispatch" not in answer:
        raise Exception("No dispatch found")
    
    answer = answer["dispatch"]
    
    dispatch = {}
    
    for circuit_id, shots in answer:
        if shots > 0:
            provider = repository[circuit_id]["provider"]
            backend = repository[circuit_id]["backend"]
            circuit = repository[circuit_id]["circuit"]
            if provider not in dispatch:
                dispatch[provider] = {}
            if backend not in dispatch[provider]:
                dispatch[provider][backend] = ([], [])
            dispatch[provider][backend][0].append(circuit)
            dispatch[provider][backend][1].append(shots)
            
    perf_store("asp", "dispatch", dispatch)
        
    return dispatch

def update_partial_distributions(partial_distributions):
    d = Dispatcher()
    return d.get_results(partial_distributions)


if __name__ == "__main__":
    print(run_asp("./src/dispatch_policies/dispatch_policy.lp"))
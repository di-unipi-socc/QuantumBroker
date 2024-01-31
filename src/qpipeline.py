import os
import sys
import time
import random
import distance as dist
import dictances
import itertools

from components.translator import Translator
from components.dispatcher import Dispatcher
from components.virtual_provider import VirtualProvider, set_ibmq_token, set_ionq_token
from components.compilation_manager import CompilationManager

from qiskit import Aer
from qiskit.quantum_info import Statevector

from components.utils.logger import *

set_ibmq_token("")
set_ionq_token("")

distances = ["total_variation", "hellinger" ]

def from_dicts_to_lists(d1, d2):
    k1 = list(d1.keys())
    k2 = list(d2.keys())
    k = list(set(k1 + k2))
    v1 = []
    v2 = []
    for key in k:
        if key in d1:
            v1.append(d1[key])
        else:
            v1.append(0)
        if key in d2:
            v2.append(d2[key])
        else:
            v2.append(0)
    return v1, v2
    
    

def compute_distance(first, second, distance):
    if first is None or second is None:
        return None
    
    if type(first) == dict:
        s = sum(v for v in first.values())
        first = {k: v/s for k,v in first.items()}
    elif type(first) == list:
        s = sum(first)
        first = [v/s for v in first]
    if type(second) == dict:
        s = sum(v for v in second.values())
        second = {k: v/s for k,v in second.items()}
    elif type(second) == list:
        s = sum(second)
        second = [v/s for v in second]
        
    
    if distance == "total_variation":
        return dictances.total_variation(first, second)
    elif distance == "hellinger":
        first, second = from_dicts_to_lists(first, second)
        return dist.hellinger(first, second)
    else:
        log_error("QPipeline: Invalid distance {}".format(distance))
    
        
def analyse(filename):
    
    with open(filename, "r") as f:
        data = json.load(f)
        
    for circuit_name, experiment in data["experiments"].items():
        ground_truth = None
        if "ground_truth" in experiment and "plain" in experiment["ground_truth"]["data"]:
            ground_truth = experiment["ground_truth"]["data"]["plain"]["results"]
        for backend_size, round in experiment["experiments"].items():
            for idx, exp_data in enumerate(round):
                backends = exp_data["backends"]
                total_results = exp_data["results"]["total"]
                for provider, backend in backends:
                    for compiler, results in exp_data["data"][provider][backend].items():
                        single_ground_truth = None
                        if "compiled" in experiment["ground_truth"]["data"]:
                            if provider in experiment["ground_truth"]["data"]["compiled"]:
                                if backend in experiment["ground_truth"]["data"]["compiled"][provider]:
                                    if compiler in experiment["ground_truth"]["data"]["compiled"][provider][backend]:
                                        single_ground_truth = experiment["ground_truth"]["data"]["compiled"][provider][backend][compiler]["results"]
                        
                        qc_baseline = None
                        if "qc_baseline" in experiment:
                            if provider in experiment["qc_baseline"]["data"]:
                                if backend in experiment["qc_baseline"]["data"][provider]:
                                    if compiler in experiment["qc_baseline"]["data"][provider][backend]:
                                        qc_baseline = experiment["qc_baseline"]["data"][provider][backend][compiler]["results"]
                        
                        if "distances" not in exp_data["metrics"]:
                            exp_data["metrics"]["distances"] = {}
                        
                        for d in distances:
                            if d not in exp_data["metrics"]["distances"]:
                                exp_data["metrics"]["distances"][d] = {}
                            if ground_truth is not None:
                                exp_data["metrics"]["distances"][d]["ground_truth"] = compute_distance(total_results, ground_truth, d)
                                print(provider, backend, compiler, total_results, ground_truth, exp_data["metrics"]["distances"][d]["ground_truth"])
                            if single_ground_truth is not None:
                                if "single" not in exp_data["metrics"]["distances"][d]:
                                    exp_data["metrics"]["distances"][d]["single"] = {}
                                if provider not in exp_data["metrics"]["distances"][d]["single"]:
                                    exp_data["metrics"]["distances"][d]["single"][provider] = {}
                                if backend not in exp_data["metrics"]["distances"][d]["single"][provider]:
                                    exp_data["metrics"]["distances"][d]["single"][provider][backend] = {}
                                if compiler not in exp_data["metrics"]["distances"][d]["single"][provider][backend]:
                                    exp_data["metrics"]["distances"][d]["single"][provider][backend][compiler] = {}
                                exp_data["metrics"]["distances"][d]["single"][provider][backend][compiler] = compute_distance(results["results"], single_ground_truth, d)
                                print(provider, backend, compiler, results["results"], single_ground_truth, exp_data["metrics"]["distances"][d]["single"][provider][backend][compiler])
                                
                            if qc_baseline is not None:
                                exp_data["metrics"]["distances"][d]["qc_baseline"] = compute_distance(results["results"], qc_baseline, d)
                                print(provider, backend, compiler, results["results"], qc_baseline, exp_data["metrics"]["distances"][d]["qc_baseline"])
                        
        
        
    with open("analysis-"+filename, "w") as f:
        json.dump(data, f)
        

if __name__ == "__main__":
    log_info("QPipeline: Starting QPipeline...")
    
    circuits = True
    providers = ["ibmq", "braket"]
    backends = None
    no_simulators = False
    only_simulators = True
    compilers = True
    metric = None # "depth" # if metric = None then in all the version of the compiled circuits are considered in the same dispatch
    
    optimise = True
    ground_truth = None  # if None also all the compiled versions are computed
    qc_baseline = True
    
    dispatch_policy = "fair_split"
    dispatch_arg = 10000
    
    rounds = 5
    backend_sizes = [1, 2]
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "analysis":
            if len(sys.argv) > 2:
                analyse(sys.argv[2])
            else:
                analyse("results.json")
            exit(0)
        if sys.argv[1] == "backends":
            vp = VirtualProvider()
            for provider in vp.providers:
                print(provider)
                for backend in vp.get_backends(provider):
                    if only_simulators and (("simulator" not in backend.lower()) or (provider.lower() == "braket" and (backend.lower() == "sv1" or backend.lower() == "tn1" or backend.lower() == "dm1"))):
                        continue
                    if no_simulators and ("simulator" in backend.lower() or (provider.lower() == "braket" and (backend.lower() == "sv1" or backend.lower() == "tn1" or backend.lower() == "dm1"))):
                        continue
                    print("\t{}".format(backend))
            exit(0)
        else:
            log_error("QPipeline: Invalid argument {}".format(sys.argv[1]))
            exit(1)
    
    
    log_info("QPipeline:\nINPUT SETTINGS:\n\tcircuits = {}\n\tproviders = {}\n\tbackends = {}\n\tcompilers = {}\n\tmetric = {}\n\tdispatch_policy = {}\n\tdispatch_arg = {}\nINPUT FLAGS:\n\toptimise = {}\n\tground_truth = {}\n\tqc_baseline = {}\nEXPERIMENT SETTINGS:\n\trounds = {}\n\tbackend_sizes = {}\n".format(circuits, providers, backends, compilers, metric, dispatch_policy, dispatch_arg, optimise, ground_truth, qc_baseline, rounds, backend_sizes))
    
    
    log_info("QPipeline: Loading circuits...")
    all_circuits = os.listdir("circuits")
    if circuits is True:
        circuits = all_circuits
    else:
        if circuits is None or circuits is False:
            circuits = []
        for circuit in circuits.copy():
            if circuit not in all_circuits:
                log_error("QPipeline: Circuit {} not found".format(circuit))
                circuits.remove(circuit)
            
    if len(circuits) == 0:
        log_error("QPipeline: No valid circuits found")
        exit(1)
    else:
        log_info("QPipeline: Found {} circuits {}".format(len(circuits), circuits))
        
    log_info("QPipeline: Loading backends...")
    vp = VirtualProvider()
    all_providers = vp.providers
    
    if providers is True:
        providers = all_providers
    else:
        if providers is None or providers is False:
            providers = []
        for provider in providers.copy():
            if provider not in all_providers:
                log_error("QPipeline: Provider {} not found".format(provider))
                providers.remove(provider)
    
    all_backends = []
    for provider in providers:
        for backend in vp.get_backends(provider):
            all_backends.append((provider, backend))
    
    if backends is True:
        backends = all_backends
    else:
        if backends is None or backends is False:
            backends = all_backends
        else:
            for backend in backends.copy():
                if backend not in all_backends:
                    log_error("QPipeline: Backend {} not found".format(backend))
                    backends.remove(backend)
            for provider in providers:
                if provider not in [backend[0] for backend in backends]:
                    backends += [(provider, backend) for backend in vp.get_backends(provider)]
                    
    if no_simulators:
        backends = [backend for backend in backends if "simulator" not in backend[1].lower()]
        backend = [backend for backend in backends if (backend[0].lower() == "braket" and (backend[1].lower() == "sv1" or backend[1].lower() == "tn1" or backend[1].lower() == "dm1"))]
        
    if only_simulators:
        backend = [backend for backend in backends if ("simulator" in backend[1].lower()) or (backend[0].lower() == "braket" and (backend[1].lower() == "sv1" or backend[1].lower() == "tn1" or backend[1].lower() == "dm1"))]
                
    if len(backends) == 0:
        log_error("QPipeline: No valid backends found")
        exit(1)
    else:
        log_info("QPipeline: Found {} backends {}".format(len(backends), backends))
        
    
    log_info("QPipeline: Loading compilers...")
    cm = CompilationManager()
    all_compilers = cm.compilers
    if compilers is True:
        compilers = all_compilers
    else:
        if compilers is None or compilers is False:
            compilers = []
        for compiler in compilers.copy():
            if compiler not in all_compilers:
                log_error("QPipeline: Compiler {} not found".format(compiler))
                compilers.remove(compiler)
                
    if len(compilers) == 0:
        log_warning("QPipeline: No valid compilers found")
    else:
        log_info("QPipeline: Found {} compilers {}".format(len(compilers), compilers))
        
    if optimise is None:
        optimise = False
        
    if metric is not None and metric is not False:
        if metric is True or metric == "depth":
            def depth(circuit):
                return circuit.depth()
            metric = depth
        elif metric == "qubits":
            def qubits(circuit):
                return circuit.n_qubits
            metric = qubits
        elif metric == "gates":
            def gates(circuit):
                return circuit.n_gates
            metric = gates
        else:
            log_error("QPipeline: Invalid metric {}".format(metric))
            exit(1)
    else:
        metric = None
        
    log_info("QPipeline: Setup complete")
        
    log_info("QPipeline:\nSETTINGS\n\tcircuits = {}\n\tbackends = {}\n\tcompilers = {}\n\tmetric = {}\n\tdispatch_policy = {}\nFLAGS:\n\toptimise = {}\n\tground_truth = {}\n\tqc_baseline = {}\nEXPERIMENT SETTINGS:\n\trounds = {}\n\tbackend_sizes = {}\n".format(circuits, backends, compilers, metric, dispatch_policy, optimise, ground_truth, qc_baseline, rounds, backend_sizes))

        
    log_info("QPipeline: Starting experiments...")
    cm = CompilationManager()
    translator = Translator()
    dispatcher = Dispatcher()
    
    _circuits = {}
    
    for circuit in circuits:
        with open("circuits/{}".format(circuit), "r") as f:
            circuit_str = f.read()
        _circuits[circuit] = circuit_str
    circuits = _circuits
    
    codes = [circuit[1] for circuit in circuits.items()]
    circuit_names = [circuit[0] for circuit in circuits.items()]
    
    compiled_circuits = {}
    circuit_to_source = {}
    for provider, backend in backends:
        if provider not in compiled_circuits:
            compiled_circuits[provider] = {}
        if backend not in compiled_circuits[provider]:
            _circuits = cm.compile(codes, provider, backend, compilers, metric, optimise=optimise)
            compiled_circuits[provider][backend] = _circuits
            for idx, compiled in enumerate(_circuits):
                for compiler, compiled_circuit in compiled.items():
                    circuit_to_source[compiled_circuit] = {"circuit": circuit_names[idx], "provider": provider, "backend": backend, "compiler": compiler}
            
    data = {"circuits": {}, "experiments": {}, "settings": {}, "start_time": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
    
    data["settings"]["circuits"] = list(circuits.keys())
    data["settings"]["backends"] = backends
    data["settings"]["compilers"] = compilers
    data["settings"]["metric"] = None if metric is None else metric.__name__
    data["settings"]["dispatch_policy"] = dispatch_policy
    data["settings"]["dispatch_arg"] = dispatch_arg
    data["settings"]["optimise"] = optimise
    data["settings"]["ground_truth"] = ground_truth
    data["settings"]["qc_baseline"] = qc_baseline
    
    with open("results.json", "w") as f:
        json.dump(data, f)
    
    for circuit_name, code in circuits.items():
        data["circuits"][circuit_name] = {"circuit": code, "compiled": {}}
    
    for idx,circuit_name in enumerate(circuit_names):
        for provider in compiled_circuits:
            for backend in compiled_circuits[provider]:
                if provider not in data["circuits"][circuit_name]["compiled"]:
                    data["circuits"][circuit_name]["compiled"][provider] = {}
                if backend not in data["circuits"][circuit_name]["compiled"][provider]:
                    data["circuits"][circuit_name]["compiled"][provider][backend] = {}
                data["circuits"][circuit_name]["compiled"][provider][backend] = compiled_circuits[provider][backend][idx]
    
    simulator = Aer.get_backend('statevector_simulator')
    
    if ground_truth is None or ground_truth is True:
        
        for circuit,code in circuits.items():
            data["experiments"][circuit] = {}
            log_info("QPipeline: Computing ground truth for circuit \"{}\"".format(circuit))
            data["experiments"][circuit]["ground_truth"] = {"data": {"plain":{}, "compiled":{}}}
            qiskit_code = translator.translate(code, "qiskit")
            qiskit_code = qiskit_code.remove_final_measurements(inplace=False)
            start = time.time()
            statevector = simulator.run(qiskit_code, shots=1).result().get_statevector()
            end = time.time()
            execution_time = end - start
            probs = Statevector(statevector).probabilities_dict()
            data["experiments"][circuit]["ground_truth"]["data"]["plain"] = {"results": probs, "metrics": {"execution_time": execution_time}}
            for k,v in probs.items():
                data["experiments"][circuit]["ground_truth"]["data"]["plain"]["results"][k[::-1]] = v
                
            
    if ground_truth is None:
        
        for provider in compiled_circuits:
            for backend in compiled_circuits[provider]:
                for idx,compiled in enumerate(compiled_circuits[provider][backend]):
                    circuit_name = circuit_names[idx]
                    if provider not in data["experiments"][circuit_name]["ground_truth"]["data"]["compiled"]:
                        data["experiments"][circuit_name]["ground_truth"]["data"]["compiled"][provider] = {}
                    if backend not in data["experiments"][circuit_name]["ground_truth"]["data"]["compiled"][provider]:
                        data["experiments"][circuit_name]["ground_truth"]["data"]["compiled"][provider][backend] = {}
                    for compiler,code in compiled.items():
                        data["experiments"][circuit_name]["ground_truth"]["data"]["compiled"][provider][backend][compiler] = {}
                        log_info("QPipeline: Computing ground truth for circuit \"{}\" compiled with {} on {} {}".format(circuit_name, compiler, provider, backend))
                        qiskit_code = translator.translate(code, "qiskit")
                        qiskit_code = qiskit_code.remove_final_measurements(inplace=False)
                        start = time.time()
                        statevector = simulator.run(qiskit_code, shots=1).result().get_statevector()
                        end = time.time()
                        execution_time = end - start
                        probs = Statevector(statevector).probabilities_dict()
                        data["experiments"][circuit_name]["ground_truth"]["data"]["compiled"][provider][backend][compiler] = {"results": {}, "metrics": {"execution_time": execution_time}}
                        for k,v in probs.items():
                            data["experiments"][circuit_name]["ground_truth"]["data"]["compiled"][provider][backend][compiler]["results"][k[::-1]] = v
    
    with open("results.json", "w") as f:
        json.dump(data, f)
    
    if qc_baseline:
        log_info("QPipeline: Computing qc truth")
        dispatch = {}
        assignments = {}
        for provider, backend in backends:
            if provider not in dispatch:
                dispatch[provider] = {}
            if provider not in assignments:
                assignments[provider] = {}
            if backend not in dispatch[provider]:
                programs = []
            if backend not in assignments[provider]:
                assignments[provider][backend] = {}
                for idx,p in enumerate(compiled_circuits[provider][backend]):
                    circuit_name = circuit_names[idx]
                    if circuit_name not in assignments[provider][backend]:
                        assignments[provider][backend][circuit_name] = {}
                    for compiler,code in p.items():
                        programs.append(code)
                        assignments[provider][backend][circuit_name][compiler] = dispatch_arg
                    dispatch[provider][backend] = (programs, dispatch_arg)
                
        start = time.time()
        results = dispatcher.dispatch(dispatch, False)
        end = time.time()
        execution_time = end - start
    
        for provider in results:
            for backend in results[provider]:
                for idx, result in enumerate(results[provider][backend]):
                    circuit = dispatch[provider][backend][0][idx]
                    circuit_info = circuit_to_source[circuit]
                    circuit_name = circuit_info["circuit"]
                    compiler = circuit_info["compiler"]
                    if circuit_name not in data["experiments"]:
                        data["experiments"][circuit_name] = {}
                    if "qc_baseline" not in data["experiments"][circuit_name]:
                        data["experiments"][circuit_name]["qc_baseline"] = {"data": {}, "metrics":{"execution_time": execution_time}}
                    if provider not in data["experiments"][circuit_name]["qc_baseline"]["data"]:
                        data["experiments"][circuit_name]["qc_baseline"]["data"][provider] = {}
                    if backend not in data["experiments"][circuit_name]["qc_baseline"]["data"][provider]:
                        data["experiments"][circuit_name]["qc_baseline"]["data"][provider][backend] = {}
                    if compiler not in data["experiments"][circuit_name]["qc_baseline"]["data"][provider][backend]:
                        data["experiments"][circuit_name]["qc_baseline"]["data"][provider][backend][compiler] = {"results": {}, "dispatch": {}}
                    res = {}
                    for k, v in result.items():
                        k = tuple(str(i) for i in k)
                        res["".join(k)] = int(v)
                    data["experiments"][circuit_name]["qc_baseline"]["data"][provider][backend][compiler]["results"] = res
                    data["experiments"][circuit_name]["qc_baseline"]["data"][provider][backend][compiler]["dispatch"] = assignments[provider][backend][circuit_name][compiler]
                    
                    with open("results.json", "w") as f:
                        json.dump(data, f)
                    
    if backend_sizes is None:
        backend_sizes = [i for i in range(1, len(backends) + 1)]
                    
    for _i,backend_size in enumerate(backend_sizes):
        log_info("QPipeline: Running experiments for backend size {} ({:0.2f}%)".format(backend_size, ((_i / len(backend_sizes)) * 100)))
        
        try_all = False
        if rounds is None:
            try_all = True
            subsets = list(itertools.combinations(backends, backend_size))
            rounds = len(subsets)
            
        for round in range(rounds):
            log_info("QPipeline: Round {}/{} for backend size {} ({:0.2f}%)".format(round+1, rounds, backend_size, ((_i*rounds + round) / (len(backend_sizes) * rounds) * 100)))
            
            if try_all:
                _backends = list(subsets[round])
            else:
                _backends = random.sample(backends, backend_size)
            # log_info("QPipeline: Selected backends {}".format(_backends))
            
            if dispatch_policy is not None:
                
                if dispatch_policy == "fair_split":
                    shots = {}
                    for idx,circuit_name in enumerate(circuit_names):
                        if circuit_name not in shots:
                            shots[circuit_name] = {}
                        _size = 0
                        for compiler in compilers:
                            if compiler not in shots[circuit_name]:
                                shots[circuit_name][compiler] = {}
                            for provider, backend in _backends:
                                if provider in compiled_circuits and backend in compiled_circuits[provider] and compiler in compiled_circuits[provider][backend][idx]:
                                    _size += 1
                        for compiler in compilers:
                            for provider, backend in _backends:
                                if provider in compiled_circuits and backend in compiled_circuits[provider] and compiler in compiled_circuits[provider][backend][idx]:
                                    if provider not in shots[circuit_name][compiler]:
                                        shots[circuit_name][compiler][provider] = {}
                                    if backend not in shots[circuit_name][compiler][provider]:
                                        shots[circuit_name][compiler][provider][backend] = {}
                                    shots[circuit_name][compiler][provider][backend] = dispatch_arg // _size

                elif dispatch_policy == "same_shots":
                    shots = dispatch_arg
                elif dispatch_policy == "random_split":
                    shots = {}
                    for idx,circuit_name in enumerate(circuit_names):
                        if circuit_name not in shots:
                            shots[circuit_name] = {}
                        _size = 0
                        for compiler in compilers:
                            if compiler not in shots[circuit_name]:
                                shots[circuit_name][compiler] = {}
                            for provider, backend in _backends:
                                if provider in compiled_circuits and backend in compiled_circuits[provider] and compiler in compiled_circuits[provider][backend][idx]:
                                    _size += 1
                            max_shots = dispatch_arg
                            it = 0
                        for compiler in compilers:
                            for provider, backend in _backends:
                                if provider in compiled_circuits and backend in compiled_circuits[provider] and compiler in compiled_circuits[provider][backend][idx]:
                                    if provider not in shots[circuit_name][compiler]:
                                        shots[circuit_name][compiler][provider] = {}
                                    if backend not in shots[circuit_name][compiler][provider]:
                                        shots[circuit_name][compiler][provider][backend] = {}
                                    if it == _size - 1:
                                        shots[circuit_name][compiler][provider][backend] = max_shots
                                    else:
                                        s = random.randint(1, (max_shots - (_size - it - 1)))
                                        max_shots -= s
                                        shots[circuit_name][compiler][provider][backend] = s
                                    it += 1
                else:
                    log_error("QPipeline: Invalid dispatch policy {}".format(dispatch_policy))
                    exit(1)
            
                dispatch = {}
                assignments = {}
                for provider, backend in _backends:
                    if provider not in dispatch:
                        dispatch[provider] = {}
                    if provider not in assignments:
                        assignments[provider] = {}
                    if backend not in dispatch[provider]:
                        dispatch[provider][backend] = ([], [])
                    if backend not in assignments[provider]:
                        assignments[provider][backend] = {}
                        for idx,p in enumerate(compiled_circuits[provider][backend]):
                            circuit_name = circuit_names[idx]
                            if circuit_name not in assignments[provider][backend]:
                                assignments[provider][backend][circuit_name] = {}
                            for compiler,code in p.items():
                                dispatch[provider][backend][0].append(code)
                                if type(shots) == dict:
                                    assignments[provider][backend][circuit_name][compiler] = shots[circuit_name][compiler][provider][backend]
                                    dispatch[provider][backend][1].append(shots[circuit_name][compiler][provider][backend])
                                else:
                                    assignments[provider][backend][circuit_name][compiler] = shots
                                    dispatch[provider][backend][1].append(shots)
                            
                
                start = time.time()
                results = dispatcher.dispatch(dispatch, False)
                end = time.time()
                execution_time = end - start
                
                for provider in results:
                    for backend in results[provider]:
                        for idx, result in enumerate(results[provider][backend]):
                            circuit = dispatch[provider][backend][0][idx]
                            circuit_info = circuit_to_source[circuit]
                            circuit_name = circuit_info["circuit"]
                            compiler = circuit_info["compiler"]
                            if circuit_name not in data["experiments"]:
                                data["experiments"][circuit_name] = {}
                            if "experiments" not in data["experiments"][circuit_name]:
                                data["experiments"][circuit_name]["experiments"] = {}
                            if backend_size not in data["experiments"][circuit_name]["experiments"]:
                                data["experiments"][circuit_name]["experiments"][backend_size] = []
                            if len(data["experiments"][circuit_name]["experiments"][backend_size]) == round:
                                data["experiments"][circuit_name]["experiments"][backend_size].append({"metrics":{}})
                                data["experiments"][circuit_name]["experiments"][backend_size][-1]["backends"] = _backends
                                data["experiments"][circuit_name]["experiments"][backend_size][-1]["data"] = {}
                                data["experiments"][circuit_name]["experiments"][backend_size][-1]["results"] = {"per_compiler": {}, "total": {}}
                                data["experiments"][circuit_name]["experiments"][backend_size][-1]["metrics"]["execution_time"] = execution_time
                            if provider not in data["experiments"][circuit_name]["experiments"][backend_size][-1]["data"]:
                                data["experiments"][circuit_name]["experiments"][backend_size][-1]["data"][provider] = {}
                            if backend not in data["experiments"][circuit_name]["experiments"][backend_size][-1]["data"][provider]:
                                data["experiments"][circuit_name]["experiments"][backend_size][-1]["data"][provider][backend] = {}
                            if compiler not in data["experiments"][circuit_name]["experiments"][backend_size][-1]["data"][provider][backend]:
                                data["experiments"][circuit_name]["experiments"][backend_size][-1]["data"][provider][backend][compiler] = {"results": {}, "dispatch": {}}
                            res = {}
                            for k, v in result.items():
                                k = tuple(str(i) for i in k)
                                key = "".join(k)
                                value = int(v)
                                res[key] = value
                                if compiler not in data["experiments"][circuit_name]["experiments"][backend_size][-1]["results"]["per_compiler"]:
                                    data["experiments"][circuit_name]["experiments"][backend_size][-1]["results"]["per_compiler"][compiler] = {}
                                if key not in data["experiments"][circuit_name]["experiments"][backend_size][-1]["results"]["per_compiler"][compiler]:
                                    data["experiments"][circuit_name]["experiments"][backend_size][-1]["results"]["per_compiler"][compiler][key] = 0
                                data["experiments"][circuit_name]["experiments"][backend_size][-1]["results"]["per_compiler"][compiler][key] += value
                                
                                if key not in data["experiments"][circuit_name]["experiments"][backend_size][-1]["results"]["total"]:
                                    data["experiments"][circuit_name]["experiments"][backend_size][-1]["results"]["total"][key] = 0
                                data["experiments"][circuit_name]["experiments"][backend_size][-1]["results"]["total"][key] += value
                                
                            data["experiments"][circuit_name]["experiments"][backend_size][-1]["data"][provider][backend][compiler]["results"] = res
                            data["experiments"][circuit_name]["experiments"][backend_size][-1]["data"][provider][backend][compiler]["dispatch"] = assignments[provider][backend][circuit_name][compiler]
                            
                            with open("results.json", "w") as f:
                                json.dump(data, f)
                            
            else:
                log_info("QPipeline: No dispatch policy specified, skipping experiments")
                
        if try_all:
            rounds = None
                                
    log_info("QPipeline: Experiments complete")
    
    data["end_time"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    data["execution_time"] = (datetime.datetime.strptime(data["end_time"], "%d/%m/%Y %H:%M:%S") - datetime.datetime.strptime(data["start_time"], "%d/%m/%Y %H:%M:%S")).total_seconds()
    
    log_info("QPipeline: Saving results...")
    
    with open("results.json", "w") as f:
        json.dump(data, f)
        
    log_info("QPipeline: Results saved")
    
    log_info("QPipeline: Analysing results...")
    
    analyse("results.json")
    
    log_info("QPipeline: Results analysed")
    
    log_info("QPipeline: Exiting QPipeline")
    
    exit(0)
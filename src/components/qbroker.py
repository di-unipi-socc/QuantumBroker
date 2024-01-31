
import pytket.circuit

from typing import Callable, Dict, List, Tuple, Any, Type

from components.compilation_manager import CompilationManager
from components.dispatcher import Dispatcher
from components.translator import Translator
from components.virtual_provider import VirtualProvider

from components.utils.utils import ThreadWithReturnValue as Thread

from components.utils.logger import *

#TODO: multiple circuits together?



BACKENDS_CACHE_TIMELIMIT = 60 * 60 # 1 hour

def set_backends_cache_timelimit(timelimit: int):
    global BACKENDS_CACHE_TIMELIMIT
    BACKENDS_CACHE_TIMELIMIT = timelimit


vp = VirtualProvider()
cm = CompilationManager()
dispatcher = Dispatcher()
translator = Translator()



def compile_for_all_backends(circuit: Any, metric: bool = True, all: bool = False) -> Dict[str, Dict[str, Dict[str, Any]]]:
    available_backends = vp.get_backends()
    
    if metric:
        def metric(circuit: Any) -> int:
            c = translator.translate(circuit, pytket.circuit.Circuit)
            return c.depth()
    else:
        metric = None
    
    threads = {}
    
    for provider, backends in available_backends.items():
        threads[provider] = {}
        for backend in backends:
            thread = Thread(target=cm.compile, kwargs={"circuits": circuit, "provider": provider, "backend": backend, "metric": metric, "cache_timelimit": BACKENDS_CACHE_TIMELIMIT}, throw_exc=False)
            thread.start()
            threads[provider][backend] = thread
            
    circuits = {}
    for provider, backends in threads.items():
        for backend, thread in backends.items():
            circuit = thread.join() 
            if circuit is not None:
                if provider not in circuits:
                    circuits[provider] = {}
                if (not all) and len(circuit) > 0 and circuit[0] is not None:
                    circuits[provider][backend] = circuit[0]
                elif all:
                    circuits[provider][backend] = circuit
                
    return circuits

def translate_all_circuits(circuits: dict[str, dict[str, dict[str, Any]]], to_language: str | Any | Type) -> dict[str, dict[str, dict[str, Any]]]:
    
    translated_circuits = {}
    
    for provider, backends in circuits.items():
        translated_circuits[provider] = {}
        for backend, compilers in backends.items():
            translated_circuits[provider][backend] = {}
            for compiler, circuit in compilers.items():
                cq = translator.translate(circuit, to_language)
                translated_circuits[provider][backend][compiler] = cq
                
    return translated_circuits


def visualise_all_circuits(circuits: dict[str, dict[str, dict[str, Any]]]):
    import qiskit
    circuits = translate_all_circuits(circuits, qiskit.QuantumCircuit)
    for provider, backends in circuits.items():
        for backend, compilers in backends.items():
            for compiler, circuit in compilers.items():
                gates = 0
                for gate in circuit.count_ops().values():
                    gates += gate
                print(provider, backend, compiler, circuit.depth(), gates)
                print(circuit)
                print("\n\n")
                
def make_circuit_repository(circuits: dict[str, dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    circuit_repository = {}
    for provider, backends in circuits.items():
        for backend, compilers in backends.items():
            for compiler, circuit in compilers.items():
                circuit_name = provider + "_" + backend + "_" + compiler + "_circuit" 
                circuit_repository[circuit_name] = {"provider": provider, "backend": backend, "compiler": compiler, "circuit": circuit}
                
    return circuit_repository

def brokering(circuit: Any, get_dispatch_policy: Callable[[dict[str, dict[str, dict[str, Any]]], dict[str, dict[str, Any]], dict], dict[str, dict[str, dict[str, Any]]]], requirements: dict = {}, dispatch: bool = True, wait: bool = True) -> dict[str, dict[str, Any]]:
    import time
    import warnings
    
    log_info("QuantumBroker: Starting...")
    log_info("QuantumBroker: Getting backends...")
    log_debug(vp.get_backends())
    
    def circuit_repository(circuit):
        log_info("QuantumBroker: Compiling circuits for all backends...")
        
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        circuits = compile_for_all_backends(circuit)
        warnings.filterwarnings("default")
        
        repository = make_circuit_repository(circuits)
        return repository
    
    def backends_info():
        log_info("QuantumBroker: Getting backends info...")
        return vp.get_backends_info(cache_timelimit=BACKENDS_CACHE_TIMELIMIT)
    
    circuit_repository_thread = Thread(target=circuit_repository, args=(circuit,))
    circuit_repository_thread.start()
    
    backends_info_thread = Thread(target=backends_info)
    backends_info_thread.start()
    
    repository = circuit_repository_thread.join()
    backends = backends_info_thread.join()
    
    log_info("QuantumBroker: Retrieving dispatch policy...")
    dispatch_policy = get_dispatch_policy(repository, backends, requirements)
    
    if dispatch:
        log_info("QuantumBroker: Dispatching circuits...")
        partial_distributions = dispatcher.dispatch(dispatch_policy, asynchronous=True)
        log_info("QuantumBroker: Waiting for results...")
        log_debug(partial_distributions)
        
        if wait:
            waiting_time = 1
            
            while not dispatcher.results_ready(partial_distributions):
                
                partial_distributions = dispatcher.get_results(partial_distributions)
                
                time.sleep(waiting_time)
                
                if waiting_time >= 900: # 15 minutes
                    waiting_time = 900
                else:
                    waiting_time *= 2
            
            log_info("QuantumBroker: Done!")
            log_info("QuantumBroker: Retrieving results...")
            log_debug(partial_distributions)
            
        return partial_distributions, dispatch_policy
    else:
        return dispatch_policy

def process_partial_distributions(partial_distributions):
    results = []
    for _, backends in partial_distributions.items():
        for _, distributions in backends.items():
            for i,distribution in enumerate(distributions):
                if len(results) <= i:
                    results.append({})
                result = results[i]
                for key, value in distribution.items():
                    if key not in result:
                        result[key] = 0
                    result[key] += value
                    
    return results


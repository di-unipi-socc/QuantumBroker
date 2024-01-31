import json

import pytket.circuit
import pytket.backends
import pytket.architecture

import qiskit

from typing import List, Any, Callable

from components.translator import Translator
from components.virtual_provider import VirtualProvider
from components.utils.utils import ThreadWithReturnValue as Thread

from components.utils.logger import *

from threading import Lock


COMPILED_CIRCUITS = ".caches/.compiled_circuits.json"
cache_lock = Lock()


def tket_compiler(circuit: pytket.circuit.Circuit, device_info: dict | None = None, optimise: bool = True) -> pytket.circuit.Circuit:
    if device_info is None:
        return circuit
    backend = VirtualProvider().get_backend(device_info["provider"], device_info["backend"])
    if backend is None:
        return circuit
    if optimise:
        circuit = backend.get_compiled_circuit(circuit, optimisation_level=2)
    else:
        circuit = backend.get_compiled_circuit(circuit, optimisation_level=0)
    return circuit
    
def qiskit_compiler(circuit: qiskit.QuantumCircuit, device_info: dict | None = None, optimise: bool = True) -> qiskit.QuantumCircuit:
    if device_info is None:
        circuit = qiskit.transpile(circuit, optimization_level=3)
    else:
        basis_gates = [x.lower() for x in device_info["gate_set"]] if "gate_set" in device_info else None
        coupling_map = device_info["coupling_map"] if "coupling_map" in device_info else None
        backend_properties = device_info["properties"] if "properties" in device_info else None #TODO: get properties from somewhere for transpule
        if optimise:
            circuit = qiskit.transpile(circuit, backend_properties=backend_properties, basis_gates=basis_gates, coupling_map=coupling_map, optimization_level=3)
        else:
            circuit = qiskit.transpile(circuit, backend_properties=backend_properties, basis_gates=basis_gates, coupling_map=coupling_map, optimization_level=0)
    return circuit

class CompilationManager:
        
    def __init__(self):
        self._translator = Translator()
        self._virtual_provider = VirtualProvider()
        
        self._compilers = {
            "tket": {
                "format": pytket.circuit.Circuit,
                "compiler": tket_compiler
            },
            "qiskit": {
                "format": qiskit.QuantumCircuit,
                "compiler": qiskit_compiler
            }
        }
        
    def _compile_circuit(self, circuit: Any, compiler: dict, device: pytket.backends.backend.Backend | None = None, device_info: dict | None = None, optimise: bool = True) -> Any | None:
        
        provider_name = device_info["provider"] if device_info is not None else None
        backend_name = device_info["backend"] if device_info is not None else None
        compiler_name = compiler["compiler"].__name__
        circuit_str = str(circuit)
        
        compiled_circuits = {}  
        
        cache_lock.acquire()      
        try:
            with open(COMPILED_CIRCUITS, "r") as f:
                compiled_circuits = json.load(f)
        except:
            if not os.path.exists(".caches"):
                os.mkdir(".caches")
            with open(COMPILED_CIRCUITS, "w+") as f:
                json.dump(compiled_circuits, f)
        cache_lock.release()
        
        if provider_name is not None and backend_name is not None:
            if circuit_str in compiled_circuits:
                if provider_name in compiled_circuits[circuit_str]:
                    if backend_name in compiled_circuits[circuit_str][provider_name]:
                        if compiler_name in compiled_circuits[circuit_str][provider_name][backend_name]:
                            return compiled_circuits[circuit_str][provider_name][backend_name][compiler_name]
                        
        log_debug(f"CompilationManager._compile_circuit(compiler: {compiler['compiler'].__name__}, device: {device.backend_info.name if device is not None else None}.{device.backend_info.device_name if device is not None else None}): Compiling circuit not found in cache")
        
        try:
            translated_circuit = self._translator.translate(circuit, compiler["format"])
            compiled_circuit = compiler["compiler"](translated_circuit, device_info, optimise)
            
            if device is not None:
                compiled_circuit = self._translator.translate(compiled_circuit, pytket.circuit.Circuit)
                # just to be sure all device constarints are satisfied after any compilation (no optimisation performed)
                compiled_circuit = device.get_compiled_circuit(compiled_circuit, optimisation_level=0)
                
                if not device.valid_circuit(compiled_circuit):
                    raise Exception("Invalid compiled circuit")
            
            compiled_circuit = self._translator.translate(compiled_circuit, circuit)    
            
            if provider_name is not None and backend_name is not None:
                cache_lock.acquire()
                with open(COMPILED_CIRCUITS, "r") as f:
                    compiled_circuits = json.load(f)
                if circuit_str not in compiled_circuits:
                    compiled_circuits[circuit_str] = {}
                if provider_name not in compiled_circuits[circuit_str]:
                    compiled_circuits[circuit_str][provider_name] = {}
                if backend_name not in compiled_circuits[circuit_str][provider_name]:
                    compiled_circuits[circuit_str][provider_name][backend_name] = {}
                compiled_circuits[circuit_str][provider_name][backend_name][compiler_name] = compiled_circuit
                with open(COMPILED_CIRCUITS, "w+") as f:
                    json.dump(compiled_circuits, f)
                cache_lock.release()
                
            return compiled_circuit
        except Exception as e:
            try:
                cache_lock.release()
            except:
                pass
            log_error(f"CompilationManager._compile_circuit(compiler: {compiler['compiler'].__name__}, device: {device.backend_info.name}.{device.backend_info.device_name}): {type(e).__name__}({e})")
            return None
    
    def _compare_compiled_circuits(self, compiled_circuits: dict[str, Any], metric: Callable) -> dict[str, Any]:
        min_metric = None
        best_compiled_circuit = None
        for compiler_name, compiled_circuit in compiled_circuits.items():
            tket_circuit = self._translator.translate(compiled_circuit, pytket.circuit.Circuit)
            value = metric(tket_circuit)
            if min_metric is None or value < min_metric:
                min_metric = value
                best_compiled_circuit = {compiler_name: compiled_circuit}
                
        return best_compiled_circuit
        
    def compile(self, circuits: Any | List[Any], provider: str | None = None, backend: str | None = None, compilers: str | List[str] | None = None, metric: Callable | None = None, cache_timelimit:int = 3600, optimise: bool = True) -> List[dict[str, Any]]:
        if not isinstance(circuits, list):
            circuits = [circuits]
            
        if compilers is None:
            compilers = self._compilers
        elif isinstance(compilers, list):
            compilers = {compiler: self._compilers[compiler] for compiler in compilers}
        elif isinstance(compilers, str):
            compilers = {compilers: self._compilers[compilers]}
            
        device_info = None
        device = None
        if provider is not None and backend is not None:
            device_info = self._virtual_provider.get_backend_info(provider, backend, cache_timelimit=cache_timelimit)
            device = self._virtual_provider.get_backend(provider, backend)
            
        threads = []    
        for circuit in circuits:
            circuit_threads = {}
            for compiler_name, compiler in compilers.items():
                thread = Thread(target=self._compile_circuit, args=(circuit, compiler, device, device_info, optimise))
                thread.start()
                circuit_threads[compiler_name] = thread
                
            threads.append(circuit_threads)
            
        compiled_circuits = []
        for circuit_threads in threads:
            compiled_circuit = {}
            for compiler_name, thread in circuit_threads.items():
                result = thread.join()
                if result is not None:
                    compiled_circuit[compiler_name] = result
                
            compiled_circuits.append(compiled_circuit)
            
        if metric is not None:
            threads = []
            for compiled_circuit in compiled_circuits:
                thread = Thread(target=self._compare_compiled_circuits, args=(compiled_circuit, metric))
                thread.start()
                threads.append(thread)
                
            compiled_circuits = []
            for thread in threads:
                compiled_circuits.append(thread.join())
            
        return compiled_circuits
    
    @property  
    def compilers(self) -> dict[str, dict[str, Any]]:
        return list(self._compilers.keys())




if __name__ == "__main__":
    cm = CompilationManager()
    
    circuit = qiskit.QuantumCircuit(2)
    circuit.h(0)
    circuit.cx(0,1)
    circuit.measure_all()
    
    circuit1 = qiskit.QuantumCircuit(3)
    circuit1.h(0)
    circuit1.cx(0,1)
    circuit1.cx(1,2)
    circuit1.measure_all()
    
    print(cm.compile([circuit, circuit1], "ibmq", "ibm_kyoto", metric=lambda x: x.depth()))
import pytket.circuit
import pytket.backends

from typing import Any, List

from components.translator import Translator
from components.virtual_provider import VirtualProvider
from components.utils.utils import ThreadWithReturnValue as Thread

from components.utils.logger import *
    
    
class Dispatcher:
    
    def __init__(self):
        
        self._translator = Translator()
        self._virtual_provider = VirtualProvider()
        
    def run(self, circuits: Any | List[Any], provider: str, backend: str, shots: int = 1, asynchronous: bool = False) -> List[Any]:
        backend = self._virtual_provider.get_backend(provider, backend)
        if not isinstance(circuits, list):
            circuits = [circuits]
        circuits = [self._translator.translate(circuit, pytket.circuit.Circuit) for circuit in circuits]
        # no optimisation performed here, just check device constraints
        circuits = [backend.get_compiled_circuit(circuit, optimisation_level=0) for circuit in circuits]
        for i,circuit in enumerate(circuits):
            if not backend.valid_circuit(circuit):
                log_error(f"Circuit {i} not valid for backend {provider}.{backend.device_name}")
                raise ValueError(f"Circuit {i} not valid for backend {provider}.{backend.device_name}")
        
        if not asynchronous:
            return [dict(result.get_counts()) for result in backend.run_circuits(circuits, n_shots=shots)]
        else:
            return backend.process_circuits(circuits, n_shots=shots)
        
    
    def dispatch(self, circuits_dispatch: dict[str, dict[str, (Any | List[Any], int | List[int])]], asynchronous: bool = False) -> dict[str, dict[str, List[Any]]]:
        """
        circuits_dispatch: {provider: {backend: (circuits, shots)}}
        """
        
        log_debug(f"Dispatch Policy: {circuits_dispatch}")
    
        threads = {}
        for provider in circuits_dispatch:
            threads[provider] = {}
            for backend in circuits_dispatch[provider]:
                threads[provider][backend] = Thread(target=self.run, args=(circuits_dispatch[provider][backend][0], provider, backend, circuits_dispatch[provider][backend][1], asynchronous))
                threads[provider][backend].start()
                
        results = {}
        for provider in threads:
            for backend in threads[provider]:
                if threads[provider][backend] is not None and isinstance(threads[provider][backend], Thread):
                    res = threads[provider][backend].join()
                    if res is not None and (isinstance(res, list) or isinstance(res, dict) or isinstance(res, pytket.backends.ResultHandle)):
                        if provider not in results:
                            results[provider] = {}
                        results[provider][backend] = res
        return results
        
    def results_ready(self, handles: dict[str, dict[str, pytket.backends.ResultHandle]] | List[pytket.backends.ResultHandle], provider: str = None, backend: str = None) -> bool:
        if isinstance(handles, dict):
            for provider in handles:
                for backend_name in handles[provider]:
                    for handle in handles[provider][backend_name]:
                        if isinstance(handle, pytket.backends.ResultHandle):
                            return False
            return True
        else:
            if not isinstance(handles, list):
                handles = [handles]
            for handle in handles:
                if isinstance(handle, pytket.backends.ResultHandle):
                    return False
            return True
        
    def get_results(self, handles: dict[str, dict[str, pytket.backends.ResultHandle]] | List[pytket.backends.ResultHandle], provider: str = None, backend: str = None) -> dict[str, dict[str, List[dict[str, int]]]] | List[dict[str, int]]:
        if isinstance(handles, dict):
            results = {}
            for provider in handles:
                results[provider] = {}
                for backend_name in handles[provider]:
                    results[provider][backend_name] = []
                    backend = self._virtual_provider.get_backend(provider, backend_name)
                    for handle in handles[provider][backend_name]:
                        if isinstance(handle, pytket.backends.ResultHandle):
                            status = backend.circuit_status(handle).status
                            if status == pytket.backends.status.StatusEnum.COMPLETED:
                                results[provider][backend_name].append(dict(backend.get_result(handle).get_counts()))
                            else:
                                results[provider][backend_name].append(handle)
                        else:
                            results[provider][backend_name].append(handle)
                            
            return results
        else:
            if not isinstance(handles, list):
                handles = [handles]
            backend = self._virtual_provider.get_backend(provider, backend)
            return [dict(backend.get_result(handle).get_counts()) for handle in handles]
        
        
if __name__ == "__main__": 
    
    dispatcher = Dispatcher()
    
    import qiskit
    
    circuit = qiskit.QuantumCircuit(2, 2)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.measure([0, 1], [0, 1])
    
    circuit1 = qiskit.QuantumCircuit(2, 2)
    circuit1.x(0)
    circuit1.x(1)
    circuit1.h(0)
    circuit1.cx(0, 1)
    circuit1.measure([0, 1], [0, 1])
    
    circuit_no_measure = qiskit.QuantumCircuit(2)
    circuit_no_measure.h(0)
    circuit_no_measure.cx(0, 1)
    
    circuit_no_measure1 = qiskit.QuantumCircuit(2)
    circuit_no_measure1.x(0)    
    circuit_no_measure1.x(1)
    circuit_no_measure1.h(0)
    circuit_no_measure1.cx(0, 1)
    
    circuits = [circuit, circuit, circuit1]
    shots = [1000,20,30]
    
    r = dispatcher.dispatch({
        "ibmq": {
            "ibmq_qasm_simulator": (circuits, shots)
        },
        "braket": {
            "sv1": ([circuit, circuit1], 10)
        },
        "ionq": {
            "simulator": (circuits, shots)
        }
    }, asynchronous=True)
    
    print(r)
    print()
    r = dispatcher.get_results(r)
    print(r)
    print()
    r = dispatcher.get_results(r)
    print(r)
    print()

    
    

    
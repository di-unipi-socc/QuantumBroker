import time
import json
import random
import datetime

import pytket.backends
import pytket.architecture

import pytket.extensions.braket as pytket_braket
import pytket.extensions.qiskit as pytket_qiskit
# import pytket.extensions.qsharp as pytket_qsharp

from typing import List, Union, Any, Type

import braket.aws as braket_aws

from qiskit.circuit import QuantumCircuit
from qiskit.providers import JobStatus
from qiskit_ibm_provider import IBMProvider
from qiskit_ionq import IonQProvider
from qiskit_ibm_runtime import QiskitRuntimeService

from components.backends.IonQBackend.pytket.extensions.ionq import IonQBackend
from components.backends.IonQBackend.pytket.extensions.ionq.backends.config import set_ionq_config

from components.utils.utils import ThreadWithReturnValue as Thread

from components.utils.logger import *

from threading import Semaphore, Lock
ibmq_semaphore = Semaphore(2)

# from qiskit_ibm_provider import IBMProvider
# from qiskit_ibm_runtime import QiskitRuntimeService

ibmq_token = None
ibmq_instance = None
ionq_token = None

BACKENDS = {}

def set_ibmq_token(token: str, instance: str | None = None):
    global ibmq_token
    ibmq_token = token
    global ibmq_instance
    ibmq_instance = instance
    pytket_qiskit.set_ibmq_config(ibmq_api_token=token, instance=instance)
    # IBMProvider.save_account(token=token, instance=instance, overwrite=True)   
    QiskitRuntimeService.save_account(channel="ibm_cloud", token=token, instance=instance, set_as_default=True, overwrite=True)
    
def set_ionq_token(token: str):
    global ionq_token
    ionq_token = token
    set_ionq_config(token)

class VirtualProvider:
    
    def __init__(self):
    
        self._providers = {
            # "azure": pytket_qsharp.AzureBackend,
            "braket": pytket_braket.BraketBackend,
            "ibmq": pytket_qiskit.IBMQBackend,
            "ionq": IonQBackend,
        }
        
        self._cache_file = ".caches/.backends.json"
        self._cache_lock = Lock()
        
    @property
    def providers(self) -> List[str]:
        return list(self._providers.keys())
    
    def get_backend(self, provider: str, backend: str, serialized: bool = False) -> pytket.backends.Backend | dict | None:
        try:
            if provider == "braket":
                
                if backend.lower() == "tn1" or backend.lower() == "sv1" or backend.lower() == "dm1":
                    backend = backend.lower()
                    backend = self._providers[provider](device=backend)
                elif backend.lower() == "lucy":
                    braket_provider = "oqc"
                    device_type = "qpu"
                    backend = "Lucy"
                    region = "eu-west-2"
                    backend = self._providers[provider](device=backend, device_type=device_type, provider=braket_provider, region=region, local=False)
                elif backend.lower() == "aquila":
                    braket_provider = "quera"   
                    device_type = "qpu"
                    backend = "Aquila"
                    region = "us-east-1"
                    backend = self._providers[provider](device=backend, device_type=device_type, provider=braket_provider, region=region, local=False)
                elif backend.lower() == "forte 1":
                    braket_provider = "ionq"
                    device_type = "qpu"
                    backend = "Forte-1"
                    region = "us-east-1"
                    backend = self._providers[provider](device=backend, device_type=device_type, provider=braket_provider, region=region, local=False)
                else:
                    backend = self._providers[provider](device=backend)
            else:
                flag = False
                for _ in range(3):
                    try:
                        backend = self._providers[provider](backend)
                        flag = True
                        break
                    except Exception as e:
                        log_critical(f"VirtualProvider.get_backend(provider: {provider}, backend: {backend}): Backend not available - {type(e).__name__}({e})")
                        time.sleep(60)
                        
                if not flag:
                    return None
            if not serialized:
                return backend
            else:
                return backend.to_dict()
        except Exception as e:
            log_error(f"VirtualProvider.get_backend(provider: {provider}, backend: {backend}, serialized: {serialized}): {type(e).__name__}({e})")
            raise e
        
    def _get_provider_backends(self, provider: str, serialized: bool = False) -> List[str] | List[dict]:
        try:
            if not serialized:
                return [backend.device_name for backend in self._providers[provider].available_devices()]
            else:
                return [backend.to_dict() for backend in self._providers[provider].available_devices()]
        except Exception as e:
            log_error(f"VirtualProvider._get_provider_backends(provider: {provider}, serialized: {serialized}): {type(e).__name__}({e})")
            return []
    
    def get_backends(self, provider: str | None = None, serialized: bool = False) -> List[str] | List[dict]:
        global BACKENDS
        if not serialized and BACKENDS != {}:
            if provider is None:
                return BACKENDS
            else:
                return BACKENDS[provider]
            
        if provider is None:
            threads = {}
            for provider in self._providers:
                threads[provider] = Thread(target=self._get_provider_backends, args=(provider, serialized))
                threads[provider].start()
                
            backends = {}
            for provider in threads:
                res = threads[provider].join()
                if res is not None and len(res) > 0:
                    backends[provider] = res
                    
            if not serialized:
                BACKENDS = backends

            return backends
        else:
            return self._get_provider_backends(provider, serialized)
        
    def _get_provider_backends_info(self, provider, cache_timelimit: int = 3600) -> dict[str, Any] | None:
        threads = {}
        try:
            devices = self._providers[provider].available_devices()
            for backend in devices:
                try: 
                    thread = Thread(target=self.get_backend_info, args=(provider, backend.device_name, cache_timelimit))
                    thread.start()
                    threads[backend.device_name] = thread
                except Exception as e:
                    log_error(f"VirtualProvider._get_provider_backends_info(provider: {provider}, backend: {backend.device_name}): {type(e).__name__}({e})")

            backends = {}
            for backend in threads:
                res = threads[backend].join()
                if res is not None:
                    backends[backend] = res
        except Exception as e:
            log_error(f"VirtualProvider._get_provider_backends_info(provider: {provider}): {type(e).__name__}({e})")
            backends = {}
            
        return backends
        
    def get_backends_info(self, provider: str | None = None, cache_timelimit: int = 3600) -> dict[str, dict[str, dict[str, Any]]] | List[dict[str, Any]]:
        if provider is None:
            threads = {}
            for provider in self._providers:
                threads[provider] = Thread(target=self._get_provider_backends_info, args=(provider,cache_timelimit))
                threads[provider].start()
            
            backends = {}
            for provider in threads:
                res = threads[provider].join()
                if res is not None:
                    backends[provider] = res
            return backends
    
        else:
            return self._get_provider_backends_info(provider, cache_timelimit)
        
    def get_backend_info(self, provider: str, backend: str, cache_timelimit:int = 3600) -> dict[str, Any] | None:
        
        self._cache_lock.acquire()
        try:
            with open(self._cache_file, "r") as f:
                backends_info = json.load(f)
        except:
            backends_info = {}
        self._cache_lock.release()
            
        if provider in backends_info and backend in backends_info[provider]:
            if "last_update" in backends_info[provider][backend] and (datetime.datetime.now(datetime.UTC) - datetime.datetime.fromisoformat(backends_info[provider][backend]["last_update"])).total_seconds() <= cache_timelimit:
                return backends_info[provider][backend]
        
        log_debug(f"VirtualProvider.get_backend_info(provider: {provider}, backend: {backend}): updating info")
        
        exc = None

        for _ in range(3):
            try:
                info = {}
                
                backend_info = self.get_backend(provider, backend)
                if backend_info is None:
                    raise Exception("Backend not found")
                else:
                    backend_info = backend_info.backend_info
                    
                info["last_update"] = datetime.datetime.now(datetime.UTC).isoformat()
                info["provider"] = provider
                info["backend"] = backend
                info["qubits"] = backend_info.n_nodes
                info["gate_set"] = [gate.name for gate in backend_info.gate_set] 
                info["misc"] = backend_info.misc
                info["simulator"] = False
                
                if "simulator" in backend or (provider == "braket" and backend.lower() == "sv1") or (provider == "braket" and backend.lower() == "tn1") or (provider == "braket" and backend == "dm1"):
                    info["simulator"] = True
                
                if isinstance(backend_info.architecture, pytket.architecture.FullyConnected) or len(backend_info.architecture.coupling) == (len(backend_info.architecture.nodes) * (len(backend_info.architecture.nodes) - 1)):
                    info["fully_connected"] = True
                else:
                    info["fully_connected"] = False
                    info["coupling_map"] = []
                    for n1, n2 in backend_info.architecture.coupling:
                        info["coupling_map"].append([n1.index[0], n2.index[0]])
                
                old_info = info.copy()
                info = self.get_provider_specific_info(provider, backend, backend_info, info.copy())
                
                if info is None:
                    info = old_info
                
                self._cache_lock.acquire()  
                try:
                    with open(self._cache_file, "r") as f:
                        backends_info = json.load(f)
                except:
                    backends_info = {}
                    
                if provider not in backends_info:
                    backends_info[provider] = {}
                backends_info[provider][backend] = info
                
                if not os.path.exists(".caches"):
                    os.mkdir(".caches")
                
                with open(self._cache_file, "w") as f:
                    json.dump(backends_info, f, indent=4)
                self._cache_lock.release()
                        
                return info
            except Exception as e:
                log_error(f"VirtualProvider.get_backend_info(provider: {provider}, backend: {backend}): {type(e).__name__}({e})")
                exc = e
                time.sleep(60)
                

        if "backend_info" not in locals():
            log_critical(f"VirtualProvider.get_backend_info(provider: {provider}, backend: {backend}): {type(exc).__name__}({exc})")
        else:
            log_critical(f"VirtualProvider.get_backend_info(provider: {provider}, backend: {backend}): {type(exc).__name__}({exc}) - {backend_info}")
        return None

    def get_provider_specific_info(self, provider: str, backend: str, backend_info: pytket.backends.backendinfo.BackendInfo, info: dict[str, Any]) -> dict[str, Any]:
        if provider == "braket":
            return self.get_braket_info(backend, backend_info, info)
        elif provider == "ibmq":
            return self.get_ibmq_info(backend, backend_info, info)
        elif provider == "ionq":
            return self.get_ionq_info(backend, backend_info, info)
        else:
            return info
            

    def get_braket_info(self, backend: str, backend_info: pytket.backends.backendinfo.BackendInfo, info: dict[str, Any]) -> dict[str, Any]:
        
        backend_ = self.get_backend("braket", backend)
        arn = backend_._device._arn
        device = braket_aws.AwsDevice(arn)
        
        technology = "not_available"
        summary = device.properties.service.deviceDocumentation.summary
        if "superconducting" in summary.lower():
            technology = "superconducting"
        elif "ion-trap" in summary.lower() or "ion trap" in summary.lower() or "trapped ion" in summary.lower():
            technology = "ion_trap"
        elif "photonic" in summary.lower():
            technology = "photonic"
        elif "neutral atom" in summary.lower() or "neutral-atom" in summary.lower():
            technology = "neutral_atom"
        elif "topological" in summary.lower():
            technology = "topological"
        elif "simulator" in summary.lower():
            technology = "simulator"
                
        info["technology"] = technology
        info["max_shots"] = int(device.properties.service.shotsRange[1])
        info["max_circuits"] = device._default_max_parallel
        info["pending_jobs"] = int(device.queue_depth().jobs) 
        info["is_free"] = True if device.properties.service.deviceCost is None or device.properties.service.deviceCost.price == 0 else False
        info["cost"] = []
        
        if backend.lower() == "dm1":
            info["cost"] = [(0.075, "minute")]
        elif backend.lower() == "sv1":
            info["cost"] = [(0.075, "minute")]
        elif backend.lower() == "tn1": 
            info["cost"] = [(0.275, "minute")]
        elif backend.lower() == "lucy":
            info["cost"] = [(0.30, "circuit"), (0.00035, "shot")]

        
        info["waiting_time"] = int(device.queue_depth().jobs) * 3600 #TODO: no information available about the waiting time so we use the number of pending jobs as a proxy
    
        
        return info

    def get_ibmq_info(self, backend: str, backend_info: pytket.backends.backendinfo.BackendInfo, info: dict[str, Any]) -> dict[str, Any]:
        try:
            b = IBMProvider().get_backend(backend)
            info["technology"] = "simulator" if "simulator" in backend.lower() else "superconducting"
            info["max_shots"] = b.max_shots
            info["max_circuits"] = b.max_experiments
            info["pending_jobs"] = b.status().pending_jobs
            info["is_free"] = True
            if "credits_required" in b.to_dict() and b.to_dict()["credits_required"]:
                info["is_free"] = False
            info["cost"] = [(1.60, "second")]
            
            ibmq_semaphore.acquire()
            
            circuit = QuantumCircuit(1)
            time.sleep(60)
            time.sleep(random.randint(0, 60))
            job = b.run(circuit)
            queue_info = None
            
            if job.status() != JobStatus.DONE:
                for _ in range(3):
                    try:
                        queue_info = job.queue_info()
                        if queue_info is not None:
                            break
                    except Exception as e:
                        log_debug(f"VirtualProvider.get_ibmq_info(backend: {backend}): {type(e).__name__}({e})")
                        if job.status() == JobStatus.DONE or job.status() == JobStatus.CANCELLED or job.status() == JobStatus.ERROR or job.status() == JobStatus.RUNNING:
                            break
                        pass
                    time.sleep(60)
                    
                if job.status() != JobStatus.DONE:
                    for _ in range(3):
                        try:
                            job.cancel()
                            break
                        except Exception as e:
                            log_debug(f"VirtualProvider.get_ibmq_info(backend: {backend}): {type(e).__name__}({e})")
                            if job.status() == JobStatus.DONE or job.status() == JobStatus.CANCELLED or job.status() == JobStatus.ERROR or job.status() == JobStatus.RUNNING:
                                break
                            pass
                        time.sleep(60)
                        
                try:
                    time.sleep(15)
                    job.cancel()
                except:
                    pass
                
            ibmq_semaphore.release()
            
            waiting_time = 0
            if queue_info is not None:
                waiting_time = (queue_info.estimated_complete_time - datetime.datetime.now(datetime.UTC)).total_seconds()
                
            info["waiting_time"] = round(waiting_time)
            
        except Exception as e:
            log_error(f"VirtualProvider.get_ibmq_info(backend: {backend}): {type(e).__name__}({e})")
            
        return info

    def get_ionq_info(self, backend: str, backend_info: pytket.backends.backendinfo.BackendInfo, info: dict[str, Any]) -> dict[str, Any]:
        info["technology"] = "ion_trap"
        
        b = IonQProvider(ionq_token).get_backend("ionq_"+backend)
        
        max_shots = b.configuration().max_shots
        
        info["max_shots"] = max_shots if max_shots is not None and max_shots != 1 else 1000000 #1000000 priate communication with IonQ (not the real maximum but practial one w.r.t. error rate)
        info["max_circuits"] = b.configuration().max_experiments
        info["pending_jobs"] = b.status().pending_jobs
        if "simulator" in backend.lower():
            info["is_free"] = True
        info["waiting_time"] = int(backend_info.misc["average_queue_time"])
        info["cost"] = []
        
        return info

if __name__ == "__main__":
    import json
    vp = VirtualProvider()
    
    info = vp.get_backends_info()
    print(info)
    json.dump(info, open(".backends.json", "w"), indent=4)
    
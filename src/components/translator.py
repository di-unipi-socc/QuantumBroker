import tempfile

import pytket.circuit
import pytket.qasm
import pytket.quipper

import pytket.extensions.braket as pytket_braket
import braket.circuits

import pytket.extensions.cirq as pytket_cirq
import cirq

import pytket.extensions.pyquil as pytket_pyquil
import pyquil

import pytket.extensions.qiskit as pytket_qiskit
import qiskit

import components.backends.IonQBackend.pytket.extensions.ionq as pytket_ionq

import pytket.extensions.pennylane as pytket_pennylane
import pennylane

import pytket.qir as pytket_qir

# import pytket.extensions.qsharp as pytket_qsharp

from typing import List, Union, Any, Type

from components.utils.logger import *

def not_implemented(_):
    raise NotImplementedError("Translation not implemented")
    
def circuit_from_quipper_str(circuit: str) -> pytket.circuit.Circuit:
    with tempfile.NamedTemporaryFile("w", suffix=".qpy") as f:
        f.write(circuit)
        f.flush()
        return pytket.quipper.circuit_from_quipper(f.name)

class Translator:
    
    def __init__(self):
        self._languages = {
            "braket": {
                "format": braket.circuits.Circuit,
                "translate_from": pytket_braket.braket_to_tk,
                "translate_to": pytket_braket.tk_to_braket
            },
            "cirq": {
                "format": cirq.Circuit,
                "translate_from": pytket_cirq.cirq_to_tk,
                "translate_to": pytket_cirq.tk_to_cirq
            },
            "ionq": {
                "format": tuple,
                "translate_from": not_implemented,
                "translate_to": pytket_ionq.backends.ionq.tk_to_ionq
            },
            "openqasm2": {
                "format": str,
                "translate_from": pytket.qasm.circuit_from_qasm_str,
                "translate_to": pytket.qasm.circuit_to_qasm_str
            },
            "pennylane": {
                "format": List[pennylane.operation.Operation],
                "translate_from": pytket_pennylane.pennylane_to_tk,
                "translate_to": not_implemented,
            },
            "pyquil": {
                "format": pyquil.quil.Program,
                "translate_from": pytket_pyquil.pyquil_to_tk,
                "translate_to": pytket_pyquil.tk_to_pyquil
            },
            "qir": {
                "format": Union[str, bytes],
                "translate_from": not_implemented,
                "translate_to": pytket_qir.pytket_to_qir
            },
            "qiskit": {
                "format": qiskit.QuantumCircuit,
                "translate_from": pytket_qiskit.qiskit_to_tk,
                "translate_to": pytket_qiskit.tk_to_qiskit
            },
            # "qsharp": {
            #     "format": str,
            #     "translate_from": not_implemented,
            #     "translate_to": pytket_qsharp.tk_to_qsharp
            # },
            "quil": {
                "format": str,
                "translate_from": lambda x: pytket_pyquil.pyquil_to_tk(pyquil.parser.parse_program(x)),
                "translate_to": lambda x: (pytket_pyquil.tk_to_pyquil(x)).out()
            },
            "quipper": {
                "format": str,
                "translate_from": circuit_from_quipper_str,
                "translate_to": not_implemented
            },
            "tket": {
                "format": pytket.circuit.Circuit,
                "translate_from": lambda x: x,
                "translate_to": lambda x: x
            }       
        }
        
        self._circuit_formats = {}
        for language in self._languages:
            format_ = self._languages[language]["format"]
            if format_ not in self._circuit_formats:
                self._circuit_formats[format_] = []
            self._circuit_formats[format_].append(language)
            
    @property   
    def languages(self) -> List[str]:
        return list(self._languages.keys())
    
    @property
    def circuit_formats(self) -> List[type]:
        return list(self._circuit_formats.keys())
    
    @property
    def language_formats(self) -> dict[str, type]:
        return {language: self._languages[language]["format"] for language in self._languages}
        
    def which(self, circuit: Any | Type) -> List[str]:
        if not isinstance(circuit, type):
            circuit = type(circuit)
            
        if circuit in self._circuit_formats:
            return self._circuit_formats[circuit]
        else:
            return []
        
    def translate(self, circuit: Any, to_language: str | Any | Type, from_language: str | None = None) -> Any:
        if from_language is None:
            from_language = self.which(circuit)
            if len(from_language) == 0:
                raise ValueError("Could not determine language of circuit")
            
        if not isinstance(from_language, list):
            from_language = [from_language]
            
        if not (isinstance(to_language, str) and to_language in self._languages):
            to_language = self.which(to_language)
            if len(to_language) == 0:
                raise ValueError("Could not determine language of output circuit")
            if len(to_language) > 1:
                # TODO: uncomment this
                # log_warning("Ambiguous output languages "+str(to_language)+" choosing first...")
                pass
            to_language = to_language[0]
            
        if len(from_language) == 1 and to_language == from_language[0]:
            return circuit
        
        for language in from_language:
            flag = False
            try:
                circuit = self._languages[language]["translate_from"](circuit)
                flag = True
                return self._languages[to_language]["translate_to"](circuit)
            except Exception as e:
                exc = str(e)
                if len(exc) > 50:
                    exc = exc[:50]+"..."
                if not flag:
                    log_error("Could not translate from {} to the intermediate language in ({}->{}): {}({})".format(language, language, to_language, type(e).__name__, exc))
                else:
                    log_error("Could not translate from the intermediate language to {} in ({}->{}): {}({})".format(to_language, language, to_language, type(e).__name__, exc))
            
        raise ValueError("Could not translate circuit from {} to {}".format(from_language, to_language))


if __name__ == "__main__":
    
    translator = Translator()
    
    print(translator.languages)
    print(translator.circuit_formats)
    print(translator.language_formats)
    
    qiskit_circuit = qiskit.QuantumCircuit(2)
    qiskit_circuit.h(0)
    qiskit_circuit.cx(0,1)
    qiskit_circuit.measure_all()
    
    tket_circuit = translator.translate(qiskit_circuit, "tket")
    print(tket_circuit)
    
    quil_circuit = translator.translate(qiskit_circuit, "quil")
    print(quil_circuit)
    
    qasm_circuit = translator.translate(qiskit_circuit, "openqasm2")
    print(qasm_circuit)
    
    braket_circuit = translator.translate(qiskit_circuit, braket.circuits.Circuit())
    print(braket_circuit)
    
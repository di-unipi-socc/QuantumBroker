#script(python)
import math
import json
import clingo

def compute_circuit_cost(shots, execution_time, provider_id, backend_id, is_free, pricing): #dollars
    shots = math.ceil(shots.number)
    execution_time = float(execution_time.string) * shots # seconds
    provider_id = str(provider_id)
    backend_id = str(backend_id)
    is_free = str(is_free)
    if is_free.lower() == "true":
        is_free = True
    else:
        is_free = False
    pricing = pricing = json.loads(pricing.string.replace("'", '"'))

    cost = 0

    if not is_free:
        for value, item in pricing:
            if item == "shot":
                cost += value * shots
            elif item == "circuit":
                cost += value
            elif item == "second":
                cost += value * execution_time
            elif item == "minute":
                cost += value * execution_time / 60
            elif item == "hour":
                cost += value * execution_time / 3600
            elif item == "day":
                cost += value * execution_time / 86400
            elif item == "month":
                cost += value * execution_time / 2592000
            elif item == "year":
                cost += value * execution_time / 31536000
            else:
                raise Exception("Unknown pricing item: " + item)
        
            
    return clingo.Number(math.ceil(cost))
#end.
circuit_cost(CId, @compute_circuit_cost(S, Time, PId, BId, Free, Pricing)) :- dispatch(CId, S), circuit(CId, PId, BId, _), S > 0, backend_is_free(PId, BId, Free), circuit_execution_time(CId, Time), backend_pricing(PId, BId, Pricing).


#show dispatch/2.
% #show circuit_cost/2.

% #show waiting_time/1.
% #show total_cost/1.
% #show used_backends/1.
% #show dispatch_size/1.

packets(0..P) :- total_shots(Total_shots), granularity(Granularity), P = (Total_shots/Granularity).
shots(S) :- packets(P), granularity(Granularity), S = P*Granularity.

{ dispatch(CircuitId, S) : shots(S), S > 0} 1 :- circuit(CircuitId, _, _, _).
% 1 { dispatch(CircuitId, S) : shots(S)} 1 :- circuit(CircuitId, _, _, _). % alternative version, assess faster and check equivalence

total_load(V) :- V = #sum{S,CId : dispatch(CId, S)}.
:- total_load(V), total_shots(Total_shots), V < Total_shots. %ensure all the shots will be performed
:- total_load(V), total_shots(Total_shots), granularity(Granularity), V > Total_shots+Granularity. %ensure all the shots will be performed

:- dispatch(CId, S), shots(S), S > 0, circuit(CId, PId, BId, _), backend_max_shots(PId, BId, Max_shots), S > Max_shots.
% :- backend(PId, BId), backend_total_load(PId, BId, S), backend_max_shots(PId, BId, Max_shots), S > Max_shots. %ensure the shots will be performed by the backend % nope max shots is for singlr circuit

:- backend(PId, BId), backend_total_load(PId, BId, S), backend_max_shots(PId, BId, Max_shots), S > Max_shots. %ensure the shots will be performed by the backend

total_cost(V) :- V = #sum{Cost,CId : dispatch(CId, S), S > 0, circuit_cost(CId, Cost)}.
:- total_cost(V), max_cost(Max_cost), V > Max_cost.

waiting_time(Waiting_time) :- Waiting_time = #max{T : dispatch(CId, S), S > 0, circuit(CId, PId, BId, _), backend_waiting_time(PId, BId, T)}.
:- waiting_time(V), max_time(Max_time), V > Max_time.

used_backends(V) :- V = #sum{1,PId,BId : dispatch(CId, S), S > 0, circuit(CId, PId, BId, _)}.
used_providers(V) :- V = #sum{1,PId : dispatch(CId, S), S > 0, circuit(CId, PId, _, _)}.
dispatch_size(V) :- V = #sum{1,CId : dispatch(CId, S), S > 0}.

backend_total_load(P, B, V) :- backend(P, B), V = #sum{S,CId : dispatch(CId, S), S > 0, circuit(CId, P, B, _)}.
circuits_per_backend(P, B, V) :- backend(P, B), V = #sum{1,CId : dispatch(CId, S), S > 0, circuit(CId, P, B, _)}.

:- dispatch(CId, S), S > 0, circuit(CId, PId, BId, _), backend_technology(PId, BId, Technology), Technology != simulator. % TODO: security requirement, remove then

#minimize{V@99 : total_load(V)}. %TODO: to generate

% max circuit per backend

% shots_spreading(V) :- used_backends(Used_backends), total_load(Total_load), Ideal = Total_load/Used_backends, V = #sum{E,P,B : backend(P, B), backend_total_load(P,B,S), E1 = S-Ideal, E = |E1|}. % too slow



backend(braket, tn1).
backend_technology(braket, tn1, simulator).
backend_waiting_time(braket, tn1, 0).
backend_max_shots(braket, tn1, 1000).
backend_max_circuits(braket, tn1, 10).
backend_pending_jobs(braket, tn1, 0).
backend_is_free(braket, tn1, false).
backend_pricing(braket, tn1, "[[0.275, 'minute']]").

backend(braket, sv1).
backend_technology(braket, sv1, simulator).
backend_waiting_time(braket, sv1, 0).
backend_max_shots(braket, sv1, 100000).
backend_max_circuits(braket, sv1, 10).
backend_pending_jobs(braket, sv1, 0).
backend_is_free(braket, sv1, false).
backend_pricing(braket, sv1, "[[0.075, 'minute']]").

backend(braket, dm1).
backend_technology(braket, dm1, simulator).
backend_waiting_time(braket, dm1, 0).
backend_max_shots(braket, dm1, 100000).
backend_max_circuits(braket, dm1, 10).
backend_pending_jobs(braket, dm1, 0).
backend_is_free(braket, dm1, false).
backend_pricing(braket, dm1, "[[0.075, 'minute']]").

backend(braket, lucy).
backend_technology(braket, lucy, superconducting).
backend_waiting_time(braket, lucy, 0).
backend_max_shots(braket, lucy, 10000).
backend_max_circuits(braket, lucy, 10).
backend_pending_jobs(braket, lucy, 0).
backend_is_free(braket, lucy, false).
backend_pricing(braket, lucy, "[[0.3, 'circuit'], [0.00035, 'shot']]").

backend(ibmq, simulator_extended_stabilizer).
backend_technology(ibmq, simulator_extended_stabilizer, simulator).
backend_waiting_time(ibmq, simulator_extended_stabilizer, 0).
backend_max_shots(ibmq, simulator_extended_stabilizer, 100000).
backend_max_circuits(ibmq, simulator_extended_stabilizer, 300).
backend_pending_jobs(ibmq, simulator_extended_stabilizer, 0).
backend_is_free(ibmq, simulator_extended_stabilizer, true).
backend_pricing(ibmq, simulator_extended_stabilizer, "[[1.6, 'second']]").

backend(ibmq, simulator_mps).
backend_technology(ibmq, simulator_mps, simulator).
backend_waiting_time(ibmq, simulator_mps, 0).
backend_max_shots(ibmq, simulator_mps, 100000).
backend_max_circuits(ibmq, simulator_mps, 300).
backend_pending_jobs(ibmq, simulator_mps, 0).
backend_is_free(ibmq, simulator_mps, true).
backend_pricing(ibmq, simulator_mps, "[[1.6, 'second']]").

backend(ibmq, simulator_statevector).
backend_technology(ibmq, simulator_statevector, simulator).
backend_waiting_time(ibmq, simulator_statevector, 0).
backend_max_shots(ibmq, simulator_statevector, 100000).
backend_max_circuits(ibmq, simulator_statevector, 300).
backend_pending_jobs(ibmq, simulator_statevector, 0).
backend_is_free(ibmq, simulator_statevector, true).
backend_pricing(ibmq, simulator_statevector, "[[1.6, 'second']]").

backend(ibmq, simulator_stabilizer).
backend_technology(ibmq, simulator_stabilizer, simulator).
backend_waiting_time(ibmq, simulator_stabilizer, 0).
backend_max_shots(ibmq, simulator_stabilizer, 100000).
backend_max_circuits(ibmq, simulator_stabilizer, 300).
backend_pending_jobs(ibmq, simulator_stabilizer, 0).
backend_is_free(ibmq, simulator_stabilizer, true).
backend_pricing(ibmq, simulator_stabilizer, "[[1.6, 'second']]").

backend(ibmq, ibm_brisbane).
backend_technology(ibmq, ibm_brisbane, superconducting).
backend_waiting_time(ibmq, ibm_brisbane, -5225).
backend_max_shots(ibmq, ibm_brisbane, 100000).
backend_max_circuits(ibmq, ibm_brisbane, 300).
backend_pending_jobs(ibmq, ibm_brisbane, 38).
backend_is_free(ibmq, ibm_brisbane, false).
backend_pricing(ibmq, ibm_brisbane, "[[1.6, 'second']]").

backend(ibmq, ibm_kyoto).
backend_technology(ibmq, ibm_kyoto, superconducting).
backend_waiting_time(ibmq, ibm_kyoto, 0).
backend_max_shots(ibmq, ibm_kyoto, 100000).
backend_max_circuits(ibmq, ibm_kyoto, 300).
backend_pending_jobs(ibmq, ibm_kyoto, 6).
backend_is_free(ibmq, ibm_kyoto, false).
backend_pricing(ibmq, ibm_kyoto, "[[1.6, 'second']]").

backend(ibmq, ibm_osaka).
backend_technology(ibmq, ibm_osaka, superconducting).
backend_waiting_time(ibmq, ibm_osaka, 0).
backend_max_shots(ibmq, ibm_osaka, 100000).
backend_max_circuits(ibmq, ibm_osaka, 300).
backend_pending_jobs(ibmq, ibm_osaka, 0).
backend_is_free(ibmq, ibm_osaka, false).
backend_pricing(ibmq, ibm_osaka, "[[1.6, 'second']]").

backend(ibmq, ibmq_qasm_simulator).
backend_technology(ibmq, ibmq_qasm_simulator, simulator).
backend_waiting_time(ibmq, ibmq_qasm_simulator, 0).
backend_max_shots(ibmq, ibmq_qasm_simulator, 100000).
backend_max_circuits(ibmq, ibmq_qasm_simulator, 300).
backend_pending_jobs(ibmq, ibmq_qasm_simulator, 0).
backend_is_free(ibmq, ibmq_qasm_simulator, true).
backend_pricing(ibmq, ibmq_qasm_simulator, "[[1.6, 'second']]").

backend(ionq, simulator).
backend_technology(ionq, simulator, simulator).
backend_waiting_time(ionq, simulator, 0).
backend_max_shots(ionq, simulator, 1000000).
backend_max_circuits(ionq, simulator, 1).
backend_pending_jobs(ionq, simulator, 0).
backend_is_free(ionq, simulator, true).
backend_pricing(ionq, simulator, "[]").



compiler(qiskit).
compiler(tket).



circuit(braket_TN1_tket_circuit, braket, tn1, tket).
circuit_depth(braket_TN1_tket_circuit, 8).
circuit_depth2q(braket_TN1_tket_circuit, 1).
circuit_width(braket_TN1_tket_circuit, 2).
circuit_bits(braket_TN1_tket_circuit, 2).
circuit_gates(braket_TN1_tket_circuit, 9).
circuit_1q_gates(braket_TN1_tket_circuit, 6).
circuit_2q_gates(braket_TN1_tket_circuit, 1).
circuit_nq_gates(braket_TN1_tket_circuit, 0).
circuit_nq_gates(braket_TN1_tket_circuit, 0).
circuit_nq_gates(braket_TN1_tket_circuit, 0).
circuit_nq_gates(braket_TN1_tket_circuit, 0).
circuit_nq_gates(braket_TN1_tket_circuit, 0).
circuit_nq_gates(braket_TN1_tket_circuit, 0).
circuit_spam_gates(braket_TN1_tket_circuit, 2).
circuit_execution_time(braket_TN1_tket_circuit, "0.0013146400451660156").


circuit(braket_SV1_tket_circuit, braket, sv1, tket).
circuit_depth(braket_SV1_tket_circuit, 8).
circuit_depth2q(braket_SV1_tket_circuit, 1).
circuit_width(braket_SV1_tket_circuit, 2).
circuit_bits(braket_SV1_tket_circuit, 2).
circuit_gates(braket_SV1_tket_circuit, 9).
circuit_1q_gates(braket_SV1_tket_circuit, 6).
circuit_2q_gates(braket_SV1_tket_circuit, 1).
circuit_nq_gates(braket_SV1_tket_circuit, 0).
circuit_nq_gates(braket_SV1_tket_circuit, 0).
circuit_nq_gates(braket_SV1_tket_circuit, 0).
circuit_nq_gates(braket_SV1_tket_circuit, 0).
circuit_nq_gates(braket_SV1_tket_circuit, 0).
circuit_nq_gates(braket_SV1_tket_circuit, 0).
circuit_spam_gates(braket_SV1_tket_circuit, 2).
circuit_execution_time(braket_SV1_tket_circuit, "0.0023691654205322266").


circuit(braket_dm1_tket_circuit, braket, dm1, tket).
circuit_depth(braket_dm1_tket_circuit, 8).
circuit_depth2q(braket_dm1_tket_circuit, 1).
circuit_width(braket_dm1_tket_circuit, 2).
circuit_bits(braket_dm1_tket_circuit, 2).
circuit_gates(braket_dm1_tket_circuit, 9).
circuit_1q_gates(braket_dm1_tket_circuit, 6).
circuit_2q_gates(braket_dm1_tket_circuit, 1).
circuit_nq_gates(braket_dm1_tket_circuit, 0).
circuit_nq_gates(braket_dm1_tket_circuit, 0).
circuit_nq_gates(braket_dm1_tket_circuit, 0).
circuit_nq_gates(braket_dm1_tket_circuit, 0).
circuit_nq_gates(braket_dm1_tket_circuit, 0).
circuit_nq_gates(braket_dm1_tket_circuit, 0).
circuit_spam_gates(braket_dm1_tket_circuit, 2).
circuit_execution_time(braket_dm1_tket_circuit, "0.009926080703735352").


circuit(braket_Lucy_tket_circuit, braket, lucy, tket).
circuit_depth(braket_Lucy_tket_circuit, 7).
circuit_depth2q(braket_Lucy_tket_circuit, 1).
circuit_width(braket_Lucy_tket_circuit, 6).
circuit_bits(braket_Lucy_tket_circuit, 2).
circuit_gates(braket_Lucy_tket_circuit, 8).
circuit_1q_gates(braket_Lucy_tket_circuit, 5).
circuit_2q_gates(braket_Lucy_tket_circuit, 1).
circuit_nq_gates(braket_Lucy_tket_circuit, 0).
circuit_nq_gates(braket_Lucy_tket_circuit, 0).
circuit_nq_gates(braket_Lucy_tket_circuit, 0).
circuit_nq_gates(braket_Lucy_tket_circuit, 0).
circuit_nq_gates(braket_Lucy_tket_circuit, 0).
circuit_nq_gates(braket_Lucy_tket_circuit, 0).
circuit_spam_gates(braket_Lucy_tket_circuit, 2).
circuit_execution_time(braket_Lucy_tket_circuit, "0.029662132263183594").


circuit(ibmq_ibmq_qasm_simulator_tket_circuit, ibmq, ibmq_qasm_simulator, tket).
circuit_depth(ibmq_ibmq_qasm_simulator_tket_circuit, 7).
circuit_depth2q(ibmq_ibmq_qasm_simulator_tket_circuit, 1).
circuit_width(ibmq_ibmq_qasm_simulator_tket_circuit, 2).
circuit_bits(ibmq_ibmq_qasm_simulator_tket_circuit, 2).
circuit_gates(ibmq_ibmq_qasm_simulator_tket_circuit, 8).
circuit_1q_gates(ibmq_ibmq_qasm_simulator_tket_circuit, 5).
circuit_2q_gates(ibmq_ibmq_qasm_simulator_tket_circuit, 1).
circuit_nq_gates(ibmq_ibmq_qasm_simulator_tket_circuit, 0).
circuit_nq_gates(ibmq_ibmq_qasm_simulator_tket_circuit, 0).
circuit_nq_gates(ibmq_ibmq_qasm_simulator_tket_circuit, 0).
circuit_nq_gates(ibmq_ibmq_qasm_simulator_tket_circuit, 0).
circuit_nq_gates(ibmq_ibmq_qasm_simulator_tket_circuit, 0).
circuit_nq_gates(ibmq_ibmq_qasm_simulator_tket_circuit, 0).
circuit_spam_gates(ibmq_ibmq_qasm_simulator_tket_circuit, 2).
circuit_execution_time(ibmq_ibmq_qasm_simulator_tket_circuit, "0.0011467933654785156").


circuit(ibmq_simulator_extended_stabilizer_qiskit_circuit, ibmq, simulator_extended_stabilizer, qiskit).
circuit_depth(ibmq_simulator_extended_stabilizer_qiskit_circuit, 14).
circuit_depth2q(ibmq_simulator_extended_stabilizer_qiskit_circuit, 2).
circuit_width(ibmq_simulator_extended_stabilizer_qiskit_circuit, 2).
circuit_bits(ibmq_simulator_extended_stabilizer_qiskit_circuit, 2).
circuit_gates(ibmq_simulator_extended_stabilizer_qiskit_circuit, 22).
circuit_1q_gates(ibmq_simulator_extended_stabilizer_qiskit_circuit, 18).
circuit_2q_gates(ibmq_simulator_extended_stabilizer_qiskit_circuit, 2).
circuit_nq_gates(ibmq_simulator_extended_stabilizer_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_extended_stabilizer_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_extended_stabilizer_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_extended_stabilizer_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_extended_stabilizer_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_extended_stabilizer_qiskit_circuit, 0).
circuit_spam_gates(ibmq_simulator_extended_stabilizer_qiskit_circuit, 2).
circuit_execution_time(ibmq_simulator_extended_stabilizer_qiskit_circuit, "0.01517176628112793").


circuit(ibmq_simulator_mps_qiskit_circuit, ibmq, simulator_mps, qiskit).
circuit_depth(ibmq_simulator_mps_qiskit_circuit, 6).
circuit_depth2q(ibmq_simulator_mps_qiskit_circuit, 2).
circuit_width(ibmq_simulator_mps_qiskit_circuit, 2).
circuit_bits(ibmq_simulator_mps_qiskit_circuit, 2).
circuit_gates(ibmq_simulator_mps_qiskit_circuit, 10).
circuit_1q_gates(ibmq_simulator_mps_qiskit_circuit, 6).
circuit_2q_gates(ibmq_simulator_mps_qiskit_circuit, 2).
circuit_nq_gates(ibmq_simulator_mps_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_mps_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_mps_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_mps_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_mps_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_mps_qiskit_circuit, 0).
circuit_spam_gates(ibmq_simulator_mps_qiskit_circuit, 2).
circuit_execution_time(ibmq_simulator_mps_qiskit_circuit, "0.00738215446472168").


circuit(ibmq_simulator_statevector_tket_circuit, ibmq, simulator_statevector, tket).
circuit_depth(ibmq_simulator_statevector_tket_circuit, 7).
circuit_depth2q(ibmq_simulator_statevector_tket_circuit, 1).
circuit_width(ibmq_simulator_statevector_tket_circuit, 2).
circuit_bits(ibmq_simulator_statevector_tket_circuit, 2).
circuit_gates(ibmq_simulator_statevector_tket_circuit, 8).
circuit_1q_gates(ibmq_simulator_statevector_tket_circuit, 5).
circuit_2q_gates(ibmq_simulator_statevector_tket_circuit, 1).
circuit_nq_gates(ibmq_simulator_statevector_tket_circuit, 0).
circuit_nq_gates(ibmq_simulator_statevector_tket_circuit, 0).
circuit_nq_gates(ibmq_simulator_statevector_tket_circuit, 0).
circuit_nq_gates(ibmq_simulator_statevector_tket_circuit, 0).
circuit_nq_gates(ibmq_simulator_statevector_tket_circuit, 0).
circuit_nq_gates(ibmq_simulator_statevector_tket_circuit, 0).
circuit_spam_gates(ibmq_simulator_statevector_tket_circuit, 2).
circuit_execution_time(ibmq_simulator_statevector_tket_circuit, "0.0012443065643310547").


circuit(ibmq_simulator_stabilizer_qiskit_circuit, ibmq, simulator_stabilizer, qiskit).
circuit_depth(ibmq_simulator_stabilizer_qiskit_circuit, 14).
circuit_depth2q(ibmq_simulator_stabilizer_qiskit_circuit, 2).
circuit_width(ibmq_simulator_stabilizer_qiskit_circuit, 2).
circuit_bits(ibmq_simulator_stabilizer_qiskit_circuit, 2).
circuit_gates(ibmq_simulator_stabilizer_qiskit_circuit, 22).
circuit_1q_gates(ibmq_simulator_stabilizer_qiskit_circuit, 18).
circuit_2q_gates(ibmq_simulator_stabilizer_qiskit_circuit, 2).
circuit_nq_gates(ibmq_simulator_stabilizer_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_stabilizer_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_stabilizer_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_stabilizer_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_stabilizer_qiskit_circuit, 0).
circuit_nq_gates(ibmq_simulator_stabilizer_qiskit_circuit, 0).
circuit_spam_gates(ibmq_simulator_stabilizer_qiskit_circuit, 2).
circuit_execution_time(ibmq_simulator_stabilizer_qiskit_circuit, "0.014299631118774414").


circuit(ibmq_ibm_brisbane_tket_circuit, ibmq, ibm_brisbane, tket).
circuit_depth(ibmq_ibm_brisbane_tket_circuit, 11).
circuit_depth2q(ibmq_ibm_brisbane_tket_circuit, 1).
circuit_width(ibmq_ibm_brisbane_tket_circuit, 80).
circuit_bits(ibmq_ibm_brisbane_tket_circuit, 2).
circuit_gates(ibmq_ibm_brisbane_tket_circuit, 14).
circuit_1q_gates(ibmq_ibm_brisbane_tket_circuit, 11).
circuit_2q_gates(ibmq_ibm_brisbane_tket_circuit, 1).
circuit_nq_gates(ibmq_ibm_brisbane_tket_circuit, 0).
circuit_nq_gates(ibmq_ibm_brisbane_tket_circuit, 0).
circuit_nq_gates(ibmq_ibm_brisbane_tket_circuit, 0).
circuit_nq_gates(ibmq_ibm_brisbane_tket_circuit, 0).
circuit_nq_gates(ibmq_ibm_brisbane_tket_circuit, 0).
circuit_nq_gates(ibmq_ibm_brisbane_tket_circuit, 0).
circuit_spam_gates(ibmq_ibm_brisbane_tket_circuit, 2).
circuit_execution_time(ibmq_ibm_brisbane_tket_circuit, "0.0009591579437255859").


circuit(ibmq_ibm_kyoto_tket_circuit, ibmq, ibm_kyoto, tket).
circuit_depth(ibmq_ibm_kyoto_tket_circuit, 11).
circuit_depth2q(ibmq_ibm_kyoto_tket_circuit, 1).
circuit_width(ibmq_ibm_kyoto_tket_circuit, 48).
circuit_bits(ibmq_ibm_kyoto_tket_circuit, 2).
circuit_gates(ibmq_ibm_kyoto_tket_circuit, 14).
circuit_1q_gates(ibmq_ibm_kyoto_tket_circuit, 11).
circuit_2q_gates(ibmq_ibm_kyoto_tket_circuit, 1).
circuit_nq_gates(ibmq_ibm_kyoto_tket_circuit, 0).
circuit_nq_gates(ibmq_ibm_kyoto_tket_circuit, 0).
circuit_nq_gates(ibmq_ibm_kyoto_tket_circuit, 0).
circuit_nq_gates(ibmq_ibm_kyoto_tket_circuit, 0).
circuit_nq_gates(ibmq_ibm_kyoto_tket_circuit, 0).
circuit_nq_gates(ibmq_ibm_kyoto_tket_circuit, 0).
circuit_spam_gates(ibmq_ibm_kyoto_tket_circuit, 2).
circuit_execution_time(ibmq_ibm_kyoto_tket_circuit, "0.0047299861907958984").


circuit(ionq_simulator_tket_circuit, ionq, simulator, tket).
circuit_depth(ionq_simulator_tket_circuit, 6).
circuit_depth2q(ionq_simulator_tket_circuit, 1).
circuit_width(ionq_simulator_tket_circuit, 2).
circuit_bits(ionq_simulator_tket_circuit, 2).
circuit_gates(ionq_simulator_tket_circuit, 7).
circuit_1q_gates(ionq_simulator_tket_circuit, 4).
circuit_2q_gates(ionq_simulator_tket_circuit, 1).
circuit_nq_gates(ionq_simulator_tket_circuit, 0).
circuit_nq_gates(ionq_simulator_tket_circuit, 0).
circuit_nq_gates(ionq_simulator_tket_circuit, 0).
circuit_nq_gates(ionq_simulator_tket_circuit, 0).
circuit_nq_gates(ionq_simulator_tket_circuit, 0).
circuit_nq_gates(ionq_simulator_tket_circuit, 0).
circuit_spam_gates(ionq_simulator_tket_circuit, 2).
circuit_execution_time(ionq_simulator_tket_circuit, "0.004716634750366211").






total_shots(10).
granularity(1).
max_cost(1000000000).
max_time(500).

#minimize{V@4 : total_cost(V)}.
#maximize{V@3 : used_backends(V)}.
#minimize{V@2 : dispatch_size(V)}.
#minimize{V@1 : waiting_time(V)}.



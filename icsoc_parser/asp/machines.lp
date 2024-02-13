machine(ionq).
status(ionq, online).
technology(ionq, trapped_ions).
qubits(ionq, 11).
language(ionq, openqasm2).
kWh(ionq, 3).
max_depth(ionq, 100).
expected_waiting_time(ionq, 0).
expected_execution_time(ionq, C, S, Res) :- circuit_depth(C, Req_depth), shots(S), Res = Req_depth*5*S.
expected_fidelity(ionq, 0).
expected_cost(ionq, C, Res) :- dispatch(ionq, C, Dispatch), Res = 1*Dispatch.
region(ionq, europe).
gates1q_speed(ionq, 3).
gates2q_speed(ionq, 3).

machine(ibm_kyiv).
status(ibm_kyiv, online).
technology(ibm_kyiv, superconductor).
language(ibm_kyiv, openqasm2).
qubits(ibm_kyiv, 127).
kWh(ibm_kyiv, 1).
max_depth(ibm_kyiv, 100).
expected_waiting_time(ibm_kyiv, 0).
expected_execution_time(ibm_kyiv, C, S, Res) :- circuit_depth(C, Req_depth), shots(S), Res = Req_depth*5*S.
expected_cost(ibm_kyiv, C, Res) :- dispatch(ibm_kyiv, C, Dispatch), Res = 5*Dispatch.
region(ibm_kyiv, europe).
gates1q_speed(ibm_kyiv, 2).
gates2q_speed(ibm_kyiv, 2).

machine(ibm_perth).
status(ibm_perth, online).
technology(ibm_perth, superconductor).
language(ibm_perth, openqasm3).
language(ibm_perth, openqasm2).
qubits(ibm_perth, 7).
kWh(ibm_perth, 2).
max_shots(ibm_perth, 20000).
max_depth(ibm_perth, 100).
expected_waiting_time(ibm_perth, 0).
expected_execution_time(ibm_perth, C, S, Res) :- circuit_depth(C, Req_depth), shots(S), Res = Req_depth*10*S.
expected_cost(ibm_perth, C, Res) :- dispatch(ibm_perth, C, Dispatch), Res = 0*Dispatch.
region(ibm_perth, europe).
gates1q_speed(ibm_perth, 3).
gates2q_speed(ibm_perth, 3).


machine(aspen_m_3).
status(aspen_m_3, online).
technology(aspen_m_3, simulator).
language(aspen_m_3, openqasm2).
qubits(aspen_m_3, 79).
max_depth(aspen_m_3, 100).
kWh(aspen_m_3, 5).
expected_waiting_time(aspen_m_3, 0).
expected_execution_time(aspen_m_3, C, S, Res) :- circuit_depth(C, Req_depth), shots(S), Res = Req_depth*3*S.
expected_cost(aspen_m_3, C, Res) :- dispatch(aspen_m_3, C, Dispatch), Res = 2*Dispatch.
region(aspen_m_3, europe).
gates1q_speed(aspen_m_3, 5).
gates2q_speed(aspen_m_3, 5).


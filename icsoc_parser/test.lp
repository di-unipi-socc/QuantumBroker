%#show compatible/2.
%#show not_compatible/2.
#show dispatch/3.
#show total_cost/1.

machine(ionq).
status(ionq, online).
technology(ionq, trapped_ions).
qubits(ionq, 11).
language(ionq, openqasm2).
kwh(ionq, 3).
max_depth(ionq, 100).
expected_waiting_time(ionq, 0).
expected_execution_time(ionq, C, Res) :- circuit_depth(C, Req_depth), Res = Req_depth*5.
expected_fidelity(ionq, 0).
expected_cost(ionq, C, Res) :- dispatch(ionq, C, Dispatch), Res = 1*Dispatch.

machine(ibm_kyiv).
status(ibm_kyiv, online).
technology(ibm_kyiv, superconductor).
language(ibm_kyiv, openqasm2).
qubits(ibm_kyiv, 127).
kwh(ibm_kyiv, 1).
max_depth(ibm_kyiv, 100).
expected_waiting_time(ibm_kyiv, 0).
expected_execution_time(ibm_kyiv, C, Res) :- circuit_depth(C, Req_depth), Res = Req_depth*3.
expected_cost(ibm_kyiv, C, Res) :- dispatch(ibm_kyiv, C, Dispatch), Res = 2*Dispatch.

machine(ibm_perth).
status(ibm_perth, online).
technology(ibm_perth, superconductor).
language(ibm_perth, openqasm3).
language(ibm_perth, openqasm2).
qubits(ibm_perth, 7).
kwh(ibm_perth, 2).
max_shots(ibm_perth, 20000).
max_depth(ibm_perth, 100).
expected_waiting_time(ibm_perth, 0).
expected_execution_time(ibm_perth, C, Res) :- circuit_depth(C, Req_depth), Res = Req_depth*10.
expected_cost(ibm_perth, C, Res) :- dispatch(ibm_perth, C, Dispatch), Res = 0*Dispatch.

machine(aspen_m_3).
status(aspen_m_3, online).
technology(aspen_m_3, simulator).
language(aspen_m_3, openqasm2).
qubits(aspen_m_3, 79).
max_depth(aspen_m_3, 100).
kwh(aspen_m_3, 5).
expected_waiting_time(aspen_m_3, 0).
expected_execution_time(aspen_m_3, C, Res) :- circuit_depth(C, Req_depth), Res = Req_depth*3.
expected_cost(aspen_m_3, C, Res) :- dispatch(aspen_m_3, C, Dispatch), Res = 2*Dispatch.


circuit(c1).
circuit_qubits(c1, 8).
circuit_depth(c1, 10).
circuit_lang(c1, openqasm2).
circuit_computer(c1, aspen_m_3).
circuit_computer(c1, ibm_perth).
circuit_computer(c1, ibm_kyiv).
circuit_computer(c1, ionq).

circuit(c2).
circuit_qubits(c2, 8).
circuit_depth(c2, 9).
circuit_lang(c2, openqasm2).
circuit_computer(c2, aspen_m_3).
circuit_computer(c2, ibm_perth).
circuit_computer(c2, ibm_kyiv).
circuit_computer(c2, ionq).

circuit(c3).
circuit_qubits(c3, 9).
circuit_depth(c3, 12).
circuit_lang(c3, openqasm2).
circuit_computer(c3, aspen_m_3).

circuit(c4).
circuit_qubits(c4, 7).
circuit_depth(c4, 11).
circuit_lang(c4, openqasm3).
circuit_computer(c4, ibm_perth).


packets(0..P) :- total_shots(Total_shots), granularity(Granularity), P = (Total_shots/Granularity).
shots(S) :- packets(P), granularity(Granularity), S = P*Granularity.

1 { compatible(M,C) ; not_compatible(M,C) } 1  :- machine(M), circuit(C), circuit_computer(C,M).

1 { dispatch(M, C, S) : shots(S) } 1 :- compatible(M, C). %distribute the shots


shots_difference(V) :- used_computers(C), total_shots(T), Ideal = T/C, V = #sum{E,M : machine_total_load(M,S), E1 = S-Ideal, E = |E1|}.
used_computers(V) :- V = #sum{1,M : dispatch(M,_,S), shots(S), S > 0}.
total_load(V) :- V = #sum{S,M,C : dispatch(M,C,S), compatible(M,C), shots(S)}.
total_cost(V) :- V = #sum{Cost,M,C : expected_cost(M,C,Cost), compatible(M,C), dispatch(M,C,S), S > 0 }.
total_time(Total_time) :- Total_time = #max{ T : machine_total_time(M, C, T), compatible(M,C), dispatch(M,C,S), S > 0 }.
machine_total_time(M, C, Total_time) :- expected_waiting_time(M, Expected_waiting_time), expected_execution_time(M, C, Expected_execution_time), Total_time = (Expected_waiting_time) + (Expected_execution_time).
machine_total_load(M, Machine_total_load) :- machine(M), Machine_total_load = #sum{S,C : dispatch(M, C, S)}.

:- compatible(M,C), qubits(M, FeatQBits), circuit_qubits(C, Req_qubits), FeatQBits < Req_qubits.
:- compatible(M,C), max_depth(M, FeatDepth), circuit_depth(C, Req_depth), FeatDepth < Req_depth.
:- compatible(M,C), language(M, FeatLang), circuit_lang(C, Req_Leang), FeatLang != Req_Leang.

:- compatible(M,_), status(M, S), S != online.
:- compatible(M,_), max_shots(M, Max), machine_total_load(M, Machine_total_load), Machine_total_load > Max.

:- total_load(V), total_shots(Total_shots), V != Total_shots. %ensure all the shots will be performed
:- total_cost(V), max_cost(Max_cost), V > Max_cost. % stay in the budget
:- total_time(V), max_time(Max_time), V > Max_time. % stay in the budget

#maximize{V : used_computers(V)}.


total_shots(20).
max_cost(10000000).
granularity(1).
max_time(99999999).
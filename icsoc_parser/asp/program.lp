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


circuit(c1).
circuit_qubits(c1, 1).
circuit_depth(c1, 10).
circuit_lang(c1, openqasm2).
gates1q(c1, 400).
gates2q(c1, 350).
circuit_computer(c1, aspen_m_3).
circuit_computer(c1, ibm_perth).
circuit_computer(c1, ibm_kyiv).
circuit_computer(c1, ionq).

% circuit(c2).
% circuit_qubits(c2, 8).
% circuit_depth(c2, 9).
% circuit_lang(c2, openqasm2).
% gates1q(c2, 200).
% gates2q(c2, 200).
% circuit_computer(c2, aspen_m_3).
% circuit_computer(c2, ibm_perth).
% circuit_computer(c2, ibm_kyiv).
% circuit_computer(c2, ionq).

% circuit(c3).
% circuit_qubits(c3, 9).
% circuit_depth(c3, 12).
% circuit_lang(c3, openqasm2).
% gates1q(c2, 100).
% gates2q(c2, 150).
% circuit_computer(c3, aspen_m_3).

% circuit(c4).
% circuit_qubits(c4, 7).
% circuit_depth(c4, 11).
% gates1q(c2, 200).
% gates2q(c2, 200).
% circuit_lang(c4, openqasm3).
% circuit_computer(c4, ibm_perth).

#show dispatch/3.
#show total_cost/1.
#show total_time/1.
%#show used_computers/1.

packets(0..P) :- total_shots(Total_shots), granularity(Granularity), P = (Total_shots/Granularity).
shots(S) :- packets(P), granularity(Granularity), S = P*Granularity.

1 { compatible(M,C) ; not_compatible(M,C) } 1  :- machine(M), circuit(C), circuit_computer(C,M).

1 { dispatch(M, C, S) : shots(S) } 1 :- compatible(M, C). %distribute the shots

:- compatible(M,C), qubits(M, FeatQBits), circuit_qubits(C, Req_qubits), FeatQBits < Req_qubits.
:- compatible(M,C), max_depth(M, FeatDepth), circuit_depth(C, Req_depth), FeatDepth < Req_depth.
:- compatible(M,C), language(M, FeatLang), circuit_lang(C, Req_Leang), FeatLang != Req_Leang.

:- compatible(M,_), status(M, S), S != online.
:- compatible(M,_), max_shots(M, Max), machine_total_load(M, Machine_total_load), Machine_total_load > Max.

:- total_load(V), total_shots(Total_shots), V != Total_shots. %ensure all the shots will be performed
:- total_cost(V), max_cost(Max_cost), V > Max_cost. % stay in the budget
:- total_time(V), max_time(Max_time), V > Max_time. % stay in the budget

shots_difference(V) :- used_computers(Comp), total_shots(T), Ideal = T/Comp, V = #sum{E,M,C : dispatch(M, C, S), E1 = S-Ideal, E = |E1|}.
used_computers(V) :- V = #sum{1,M : dispatch(M,_,S), shots(S), S > 0}.
total_load(V) :- V = #sum{S,M,C : dispatch(M,C,S), compatible(M,C), shots(S)}.
total_cost(V) :- V = #sum{Cost,M,C : expected_cost(M,C,Cost), compatible(M,C), dispatch(M,C,S), S > 0 }.
total_time(Total_time) :- Total_time = #max{ T : compatible(M,C), dispatch(M,C,S), S > 0, machine_total_time(M, C, S, T) }.
machine_total_time(M, C, S, Total_time) :- expected_waiting_time(M, Expected_waiting_time), expected_execution_time(M, C, S, Expected_execution_time), Total_time = (Expected_waiting_time) + (Expected_execution_time).
machine_total_load(M, Machine_total_load) :- machine(M), Machine_total_load = #sum{S,C : dispatch(M, C, S)}.


total_shots(20).
max_cost(10000000).
:- compatible(M, C), technology(M, Technology), Technology == simulator.
:- compatible(M, C), region(M, Region), Region != europe.
total_energy_cost(Total_energy_cost) :- Total_energy_cost = #sum{ E, M : compatible(M,C), dispatch(M,C,S), shots(S), S > 0, energy_cost(M, C, S, E) }.
energy_cost(M, C, S, Energy_cost) :- dispatch(M,C,S), shots(S), technology(M, superconductor), gates1q(C,G1), gates2q(C,G2), gates1q_speed(M,G1_speed), gates2q_speed(M,G2_speed), kWh(M, K), circuit_depth(C, Req_depth), Energy_cost = S*(G1_speed*G1 + G2_speed*G2)*K.
energy_cost(M, C, S, Energy_cost) :- dispatch(M,C,S), shots(S), technology(M, trapped_ions), gates1q(C,G1), gates2q(C,G2), gates1q_speed(M,G1_speed), gates2q_speed(M,G2_speed), kWh(M, K), Energy_cost = S*(G1_speed*G1 + G2_speed*G2)*K.
energy_cost(M, C, S, Energy_cost) :- dispatch(M,C,S), shots(S), technology(M, neutral_atoms), gates1q(C,G1), gates2q(C,G2), kWh(M, K), Energy_cost = ((G1 + G2)*S)/1000 * K.
energy_cost(M, C, S, Energy_cost) :- dispatch(M,C,S), shots(S), technology(M, simulator), gates1q(C,G1), gates2q(C,G2), kWh(M, K), Energy_cost = ((G1 + G2)*S)/10000 * K.
#minimize{Total_energy_cost@3 : total_energy_cost(Total_energy_cost)}.
#maximize{Used_computers@2 : used_computers(Used_computers)}.
#minimize{Shots_difference@1 : shots_difference(Shots_difference)}.
granularity(1).
max_time(99999999).
#show total_energy_cost/1.

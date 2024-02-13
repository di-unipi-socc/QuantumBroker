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

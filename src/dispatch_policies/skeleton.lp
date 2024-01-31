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

#minimize{V@999 : total_load(V)}.

% max circuit per backend

% shots_spreading(V) :- used_backends(Used_backends), total_load(Total_load), Ideal = Total_load/Used_backends, V = #sum{E,P,B : backend(P, B), backend_total_load(P,B,S), E1 = S-Ideal, E = |E1|}. % too slow
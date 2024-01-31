import configparser
import connexion
import uuid
import json
import sys
import os

from flask import current_app

from components.virtual_provider import set_ibmq_token, set_ionq_token
from components.qbroker import set_backends_cache_timelimit, compile_for_all_backends, BACKENDS_CACHE_TIMELIMIT

from components.dispatcher import Dispatcher
from components.translator import Translator
from components.virtual_provider import VirtualProvider
from components.qrepo import QRepository

from qbroker_asp import QuantumBroker, parse_repository, parse_backends, parse_requirements, parse_answer, run_asp, process_partial_distributions, update_partial_distributions

from components.utils.logger import *

dispatcher = Dispatcher()
qrepository = QRepository()

"""
The default app configuration: 
in case a configuration is not found or 
some data is missing
"""
DEFAULT_CONFIGURATION = { 
    "IP": "0.0.0.0", # the app ip
    "PORT": 8080, # the app port
}

DISPATCHES = ".caches/.dispatches.json"
PARTIAL_DISTRIBUTIONS = ".caches/.partial_distributions.json"

def get_saved_dispatches():
    try:
        with open(DISPATCHES, "r") as f:
            return json.load(f)
    except:
        return {}
    
def get_saved_partial_distributions():
    try:
        with open(PARTIAL_DISTRIBUTIONS, "r") as f:
            return json.load(f)
    except:
        return {}
    
def save_dispatches(dispatches):
    with open(DISPATCHES, "w+") as f:
        json.dump(dispatches, f)
        
def save_partial_distributions(partial_distributions):
    with open(PARTIAL_DISTRIBUTIONS, "w+") as f:
        json.dump(partial_distributions, f)
        
def update_saved_dispatches(key, value):
    dispatches = get_saved_dispatches()
    dispatches[key] = value
    save_dispatches(dispatches)
    
def update_saved_partial_distributions(key, value):
    partial_distributions = get_saved_partial_distributions()
    partial_distributions[key] = value
    save_partial_distributions(partial_distributions)
    

def change_keys_to_str(x):
    if isinstance(x, dict):
        return {str(k): change_keys_to_str(v) for k, v in x.items()}
    if isinstance(x, list):
        return [change_keys_to_str(v) for v in x]
    return x

def asp_policy(repository, backends, requirements):
    
    circuits = parse_repository(repository)
    infra = parse_backends(backends)
    asp_requirements = parse_requirements(requirements)
    
    policy = ""
    
    with open("src/dispatch_policies/skeleton.lp", "r") as f:
        policy = f.read()
        
    policy += infra
    policy += circuits
    policy += asp_requirements
    
    with open("src/dispatch_policies/dispatch_policy.lp", "w+") as f:
        f.write(policy)
    
    answer = run_asp("src/dispatch_policies/dispatch_policy.lp")
    
    if answer is None or len(answer) == 0 or answer == {}:
        raise Exception("No dispatch found")

    answer = parse_answer(answer, repository)

    return answer

def compute_dispatch(body):
    try:
        circuit = body["circuit"]
        requirements = body["requirements"] if "requirements" in body else {}
        
        answer = QuantumBroker(circuit=circuit, get_dispatch_policy=asp_policy, requirements=requirements, dispatch=False)
        
        answer["dispatch_id"] = str(uuid.uuid4())
        update_saved_dispatches(answer["dispatch_id"], answer)
        
        answer = change_keys_to_str(answer)
        
        return answer, 200
    except Exception as e:
        log_debug(f"QuantumBroker Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def perform_dispatch(body):

    try:
        circuit = body["circuit"]
        requirements = body["requirements"] if "requirements" in body else {}
        
        answer, dispatch = QuantumBroker(circuit=circuit, get_dispatch_policy=asp_policy, requirements=requirements, dispatch=True, wait=False)
        answer["completed"] = dispatcher.results_ready(answer)
        
        answer["dispatch_id"] = str(uuid.uuid4())
        update_saved_dispatches(answer["dispatch_id"], dispatch)
        answer["partial_distribution_id"] = str(uuid.uuid4())
        answer = change_keys_to_str(answer)
        update_saved_partial_distributions(answer["partial_distribution_id"], answer)
        return answer, 201
    except Exception as e:
        log_debug(f"QuantumBroker Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def perform_existing_dispatch(dispatch_id):
    
    dispatches = get_saved_dispatches()
    if dispatch_id not in dispatches:
        return "Not Found", 404
    
    try:
        dispatch = dispatches[dispatch_id]
        try:
            del dispatch["dispatch_id"]
        except:
            pass
        answer = dispatcher.dispatch(dispatch, asynchronous=True)
        answer["completed"] = dispatcher.results_ready(answer)
        
        answer["dispatch_id"] = dispatch_id
        answer["partial_distribution_id"] = str(uuid.uuid4())
        answer = change_keys_to_str(answer)
        update_saved_partial_distributions(answer["partial_distribution_id"], answer)
        
        return answer, 201
    except Exception as e:
        log_debug(f"QuantumBroker Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def perform_user_dispatch(body):

    try:
        try:
            del body["dispatch_id"]
        except:
            pass
        answer = dispatcher.dispatch(body, asynchronous=True)
        answer["completed"] = dispatcher.results_ready(answer)
        
        answer["dispatch_id"] = str(uuid.uuid4())
        update_saved_dispatches(answer["dispatch_id"], body)
        
        answer["partial_distribution_id"] = str(uuid.uuid4())
        answer = change_keys_to_str(answer)
        update_saved_partial_distributions(answer["partial_distribution_id"], answer)
        
        return answer, 201
    except Exception as e:
        log_debug(f"QuantumBroker Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def get_dispatch(dispatch_id):
    dispatches = get_saved_dispatches()
    if dispatch_id in dispatches:
        d = dispatches[dispatch_id]
        return change_keys_to_str(d), 200
    else:
        return "Not Found", 404
    
def get_partial_distribution(partial_distribution_id):
    partial_distributions = get_saved_partial_distributions()
    if partial_distribution_id in partial_distributions:
        partial_distribution_ = partial_distributions[partial_distribution_id].copy()
        dispatch_id = partial_distribution_["dispatch_id"]
        try:
            del partial_distribution_["dispatch_id"]
        except:
            pass
        try:
            del partial_distribution_["partial_distribution_id"]
        except:
            pass
        try:
            del partial_distribution_["completed"]
        except:
            pass
        partial_distributions[partial_distribution_id] = update_partial_distributions(partial_distribution_)
        partial_distributions[partial_distribution_id]["completed"] = dispatcher.results_ready(partial_distributions[partial_distribution_id])
        
        partial_distributions[partial_distribution_id]["dispatch_id"] = dispatch_id
        partial_distributions[partial_distribution_id]["partial_distribution_id"] = partial_distribution_id
        
        partial_distributions[partial_distribution_id] = change_keys_to_str(partial_distributions[partial_distribution_id])
        update_saved_partial_distributions(partial_distribution_id, partial_distributions[partial_distribution_id])
        return partial_distributions[partial_distribution_id], 200
    else:
        return "Not Found", 404
        
def process_existing_partial_distribution(partial_distribution_id):
    partial_distributions = get_saved_partial_distributions()
    if partial_distribution_id in partial_distributions:
        partial_distribution_ = partial_distributions[partial_distribution_id].copy()
        try:
            del partial_distribution_["dispatch_id"]
        except:
            pass
        try:
            del partial_distribution_["partial_distribution_id"]
        except:
            pass
        if partial_distribution_["completed"]:
            try:
                del partial_distribution_["completed"]
            except:
                pass
            try:
                partial_distribution_ = process_partial_distributions(partial_distribution_)
                partial_distribution_ = change_keys_to_str(partial_distribution_)
                return partial_distribution_, 200
            except Exception as e:
                log_debug(f"QuantumBroker Error: {type(e).__name__}({e})")
                return f"{type(e).__name__}({e})", 500
        else:
            return "Partial Distribution Not Ready", 400
    else:
        return "Not Found", 404    
    
def process_user_partial_distribution(body):

    try:
        if dispatcher.results_ready(body):
            body = process_partial_distributions(body)
            body = change_keys_to_str(body)
            return body, 200
        else:
            return "Partial Distribution Not Ready", 400
    except Exception as e:
        log_debug(f"QuantumBroker Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def compile(body):
    try:
        circuits = body["circuits"]
        
        compiled_circuits = compile_for_all_backends(circuits, metric=False, all=True)
        
        return {"circuits": compiled_circuits}, 200
    except Exception as e:
        log_debug(f"QuantumBroker Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def translate(body):
    try:
        circuit = body["circuit"]
        from_language = body["from_language"] if "from_language" in body else None 
        to_language = body["to_language"]
        
        translator = Translator()
        
        translated_circuit = translator.translate(circuit, to_language, from_language)
        ans = {"circuit": translated_circuit, "to_language": body["to_language"]}
        if from_language is not None:
            ans["from_language"] = body["from_language"]
        
        return ans, 200
    except Exception as e:
        log_debug(f"QuantumBroker Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def get_backends(provider=None, backend=None):
    try:
        vp = VirtualProvider()
        if provider is not None and backend is not None:
            try:
                backends = vp.get_backend_info(provider, backend, cache_timelimit=BACKENDS_CACHE_TIMELIMIT)
            except Exception as e:
                if str(e) == "Backend not found":
                    return "Backend Not Found", 404
                elif str(e) == "Backend not available":
                    return "Backend Not Available", 400
        else:
            backends = vp.get_backends_info(provider, cache_timelimit=BACKENDS_CACHE_TIMELIMIT)   
        return backends, 200
    except Exception as e:
        log_debug(f"QuantumBroker Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def get_algorithms():
    try:
        algorithms = qrepository.get_algorithms_metadata()
        return algorithms, 200
    except Exception as e:
        log_debug(f"QRepository Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def add_algorithm(body):
    try:
        algorithm_id = body["algorithm_id"]
        description = body["description"] if "description" in body else ""
        schema = body["schema"] if "schema" in body else None
        qrepository.push_algorithm(algorithm_id, description, schema)
        return "OK", 201
    except Exception as e:
        log_debug(f"QRepository Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def get_algorithm(algorithm_id):
    try:
        algorithm = qrepository.get_algorithm_metadata(algorithm_id)
        return algorithm, 200
    except Exception as e:
        log_debug(f"QRepository Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def run_algorithm(algorithm_id, body):    
    try:
        algorithm = qrepository.run_algorithm(algorithm_id, body)
        return algorithm, 200
    except Exception as e:
        log_debug(f"QRepository Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def delete_algorithm(algorithm_id):
    try:
        qrepository.delete_algorithm(algorithm_id)
        return "OK", 204
    except Exception as e:
        log_debug(f"QRepository Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def get_circuits(algorithm_id):
    try:
        circuits = qrepository.get_circuits_metadata(algorithm_id)
        return circuits, 200
    except Exception as e:
        log_debug(f"QRepository Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def add_circuit(algorithm_id, body):
    try:
        circuit_id = body["circuit_id"]
        circuit = body["circuit"]
        schema = body["schema"] if "schema" in body else None
        function = body["function"] if "function" in body else None
        priority = body["priority"] if "priority" in body else None
        description = body["description"] if "description" in body else ""
        qrepository.push_circuit(algorithm_id, circuit_id, circuit, schema, function, priority, description)
        return "OK", 201
    except Exception as e:
        log_debug(f"QRepository Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def get_circuit(algorithm_id, circuit_id):
    try:
        circuit = qrepository.get_circuit(algorithm_id, circuit_id)
        return circuit, 200
    except Exception as e:
        log_debug(f"QRepository Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def run_circuit(algorithm_id, circuit_id, body):
    try:
        circuit = qrepository.run_circuit(algorithm_id, circuit_id, body)
        return circuit, 200
    except Exception as e:
        log_debug(f"QRepository Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
def delete_circuit(algorithm_id, circuit_id):
    try:
        qrepository.delete_circuit(algorithm_id, circuit_id)
        return "OK", 204
    except Exception as e:
        log_debug(f"QRepository Error: {type(e).__name__}({e})")
        return f"{type(e).__name__}({e})", 500
    
    
def get_config(configuration=None):
    """ Returns a json file containing the configuration to use in the app

    The configuration to be used can be passed as a parameter, 
    otherwise the one indicated by default in config.ini is chosen

    ------------------------------------
    [CONFIG]
    CONFIG = The_default_configuration
    ------------------------------------

    Params:
        - configuration: if it is a string it indicates the configuration to choose in config.ini
    """
    try:
        parser = configparser.ConfigParser()
        if parser.read('config.ini') != []:
            
            if type(configuration) != str: # if it's not a string, take the default one
                configuration = parser["CONFIG"]["CONFIG"]

            log_debug("QBrokerService Configuration: "+configuration)
            configuration = parser._sections[configuration] # get the configuration data
            configuration = {**parser._sections["CONFIG"].copy(), **configuration.copy()} # add the default configuration data

            parsed_configuration = {}
            for k,v in configuration.items(): # Capitalize keys and translate strings (when possible) to their relative number or boolean
                k = k.upper()
                parsed_configuration[k] = v
                try:
                    parsed_configuration[k] = int(v)
                except:
                    try:
                        parsed_configuration[k] = float(v)
                    except:
                        if v == "true":
                            parsed_configuration[k] = True
                        elif v == "false":
                            parsed_configuration[k] = False
                        elif v == "none" or v == "null":
                            parsed_configuration[k] = None

            for k,v in DEFAULT_CONFIGURATION.items():
                if not k in parsed_configuration: # if some data are missing enter the default ones
                    parsed_configuration[k] = v

            return parsed_configuration
        else:
            return DEFAULT_CONFIGURATION
    except Exception as e:
        log_debug(f"QBrokerService Configuration Error: {e.__name__}({e})")
        log_debug(f"QBrokerService Configuration: Runnng Default Configuration")
        return DEFAULT_CONFIGURATION

def setup(application, config):

    for k,v in config.items():
        application.config[k] = v # insert the requested configuration in the app configuration
        
    if "IBMQ_TOKEN" in config:
        set_ibmq_token(config["IBMQ_TOKEN"])
    if "IONQ_TOKEN" in config:
        set_ionq_token(config["IONQ_TOKEN"])
    if "BACKENDS_CACHE_TIMELIMIT" in config:
        set_backends_cache_timelimit(config["BACKENDS_CACHE_TIMELIMIT"])
    if "LOG_LEVEL" in config:
        set_log_level(config["LOG_LEVEL"])
    if "LOG_FILE" in config and config["LOG_FILE"] != "" and config["LOG_FILE"] is not None:
        if type(config["LOG_FILE"]) == str:
            set_log_file(config["LOG_FILE"])
        elif type(config["LOG_FILE"]) == bool and config["LOG_FILE"]:
            try:
                os.mkdir(".logs")
            except:
                pass
            set_log_file(".logs/qbrokerservice-{:%Y-%m-%d_%H-%M-%S}.log".format(datetime.datetime.now()))
            try:
                os.mkdir(".caches")
            except:
                pass
            set_log_file

def create_app(configuration=None):
    app = connexion.App(__name__)
    app.add_api('./qbroker.yaml')
    # set the WSGI application callable to allow using uWSGI:
    # uwsgi --http :8080 -w app
    application = app.app

    conf = get_config(configuration)
    log_debug("QBrokerService Configuration: "+str(conf))
    log_info("- QBrokerService ONLINE @ ("+conf["IP"]+":"+str(conf["PORT"])+")")

    with app.app.app_context():
        setup(application, conf)

    return app

if __name__ == '__main__':
    c = None
    if len(sys.argv) > 1: # if it is inserted
        c = sys.argv[1] # get the configuration name from the arguments

    app = create_app(c)

    with app.app.app_context():
        app.run(
            host=current_app.config["IP"], 
            port=current_app.config["PORT"]
            )
        
"""



{
    "circuit": "OPENQASM 2.0; include \"qelib1.inc\"; qreg q[2]; creg c[2]; h q[0]; h q[1]; s q[0]; s q[1]; h q[1]; cx q[0],q[1]; h q[1]; s q[0]; s q[1]; h q[0]; h q[1]; x q[0]; x q[1]; h q[1]; cx q[0],q[1]; h q[1]; x q[0]; x q[1]; h q[0]; h q[1]; measure q[0] -> c[0]; measure q[1] -> c[1];",
    "requirements":{
        "constants": {
            "total_shots": 10,
            "granularity": 1,
            "max_cost": 1000000000,
            "max_time": 500
        },
        "objectives": [
            "-total_cost",
            "used_backends",
            "-dispatch_size",
            "-waiting_time"
        ],
        "constraints": {
            "@": {
                "only_simulators": {}
            }
        }
    }
}



"""
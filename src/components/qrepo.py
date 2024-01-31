import os
import shutil
import json


from components.utils.utils import dynamic_import

class QRepository:
    
    def __init__(self):
        
        self._base_folder = "./src/components/qrepofolder/"
        self._cache = ".caches/"
        self._algorithms = {}

        if not os.path.exists(self._base_folder):
            os.mkdir(self._base_folder)
            self._create_init_file(self._base_folder)
            
        try:
            self._load()
        except:
            pass
        
    def _save(self):    
        if not os.path.exists(self._cache):
            os.mkdir(self._cache)
            
        with open(self._cache + "qrepo.json", "w+") as f:
            json.dump(self._algorithms, f)
            
    def _load(self):
        if os.path.exists(self._cache + "qrepo.json"):
            with open(self._cache + "qrepo.json", "r") as f:
                self._algorithms = json.load(f)
        
    def _create_init_file(self, folder: str):
            
            file = folder + "__init__.py"
            if os.path.exists(file):
                os.remove(file)
                
            with open(file, "w+") as f:
                f.write("")
    
    def _check_input(self, algo_schema: dict, circuit_schema: dict, params: dict):
        if algo_schema is not None and algo_schema != {}:
            for key in algo_schema:
                if type(algo_schema[key]) is dict:
                    if key not in params and "default" not in algo_schema[key]:
                        raise Exception("Input does not match algorithm schema: missing key " + key)
                    
                    if key not in params and "default" in algo_schema[key]:
                        params[key] = algo_schema[key]["default"]
                    
                    if type(params[key]).__name__ != algo_schema[key]["type"]:
                        raise Exception("Input does not match algorithm schema: wrong type for key " + key + " (expected " + algo_schema[key]["type"] + ", got " + type(params[key]).__name__ + ")")
            
                elif type(algo_schema[key]) is str:
                    if key not in params:
                        raise Exception("Input does not match algorithm schema: missing key " + key)
                    
                    if type(params[key]).__name__ != algo_schema[key]:
                        raise Exception("Input does not match algorithm schema: wrong type for key " + key + " (expected " + algo_schema[key] + ", got " + type(params[key]).__name__ + ")")
                    
                else:
                    raise Exception("Invalid algorithm schema")
                
        if circuit_schema is not None and circuit_schema != {}:
            for key in circuit_schema:
                if type(circuit_schema[key]) is dict:
                    if "type" in circuit_schema[key]:
                        if key not in params and "default" not in circuit_schema[key]:
                            raise Exception("Input does not match circuit schema: missing key " + key)
                        
                        if key not in params and "default" in circuit_schema[key]:
                            params[key] = circuit_schema[key]["default"]
                        
                        if type(params[key]).__name__ != circuit_schema[key]["type"]:
                            raise Exception("Input does not match circuit schema: wrong type for key " + key + " (expected " + circuit_schema[key]["type"] + ", got " + type(params[key]).__name__ + ")")
                    
                    if key not in params:
                        raise Exception("Input does not match circuit schema: missing key " + key)
                    
                    if "=" in circuit_schema[key]:
                        if params[key] != circuit_schema[key]["="]:
                            raise Exception("Input does not match circuit schema: wrong value for key " + key + " (expected " + circuit_schema[key]["="] + ", got " + params[key] + ")")
                    if "<" in circuit_schema[key]:
                        if params[key] >= circuit_schema[key]["<"]:
                            raise Exception("Input does not match circuit schema: wrong value for key " + key + " (expected " + circuit_schema[key]["<"] + ", got " + params[key] + ")")
                    if ">" in circuit_schema[key]:
                        if params[key] <= circuit_schema[key][">"]:
                            raise Exception("Input does not match circuit schema: wrong value for key " + key + " (expected " + circuit_schema[key][">"] + ", got " + params[key] + ")")
                    if "<=" in circuit_schema[key]:
                        if params[key] > circuit_schema[key]["<="]:
                            raise Exception("Input does not match circuit schema: wrong value for key " + key + " (expected " + circuit_schema[key]["<="] + ", got " + params[key] + ")")
                    if ">=" in circuit_schema[key]:
                        if params[key] < circuit_schema[key][">="]:
                            raise Exception("Input does not match circuit schema: wrong value for key " + key + " (expected " + circuit_schema[key][">="] + ", got " + params[key] + ")")
                    if "!=" in circuit_schema[key]:
                        if params[key] == circuit_schema[key]["!="]:
                            raise Exception("Input does not match circuit schema: wrong value for key " + key + " (expected " + circuit_schema[key]["!="] + ", got " + params[key] + ")")
            
                elif type(circuit_schema[key]) is str:
                    if key not in params:
                        raise Exception("Input does not match circuit schema: missing key " + key)
                    
                    if type(params[key]).__name__ != circuit_schema[key]:
                        raise Exception("Input does not match circuit schema: wrong type for key " + key + " (expected " + circuit_schema[key] + ", got " + type(params[key]).__name__ + ")")
                    
                else:
                    raise Exception("Invalid circuit schema")
                
        
    def push_algorithm(self, name: str, description: str = "", schema: dict = None):
        
        if name in self._algorithms:
            raise Exception("Algorithm already exists")
        
        folder = self._base_folder + name
        os.mkdir(folder)
        self._create_init_file(folder+"/")
        
        self._algorithms[name] = {"description": description, "schema": schema, "path": folder, "circuits": {}}
        
        self._save()
        
    def push_circuit(self, algorithm: str, name: str, circuit: str, schema: dict = None, function: str = None, priority: int = None, description: str = ""):
        
        if algorithm not in self._algorithms:
            raise Exception("Algorithm does not exist")
        
        if name in self._algorithms[algorithm]["circuits"]:
            raise Exception("Circuit already exists")
        
        file = self._algorithms[algorithm]["path"] + "/" + name + ".py"
            
        with open(file, "w+") as f:
            f.write(circuit)
            
        if priority is None:
            priority = len(self._algorithms[algorithm]["circuits"])
            
        self._algorithms[algorithm]["circuits"][name] = {"schema": schema, "path": file, "function": function, "priority": priority, "description": description}
        
        self._save()
        
    def run_circuit(self, algorithm: str, name: str, params: dict = {}):
        
        if algorithm not in self._algorithms:
            raise Exception("Algorithm does not exist")
        
        if name not in self._algorithms[algorithm]["circuits"]:
            raise Exception("Circuit does not exist")
        
        try:
            self._check_input(self._algorithms[algorithm]["schema"], self._algorithms[algorithm]["circuits"][name]["schema"], params)
        except Exception as e:
            raise Exception("Input does not match circuit or algoritm schemas: " + str(type(e).__name__) + "(" + str(e) + ")" )
        
        circuit = self._algorithms[algorithm]["circuits"][name]       
        
        if circuit["function"] is None:
            raise Exception("Circuit does not have a function")
        
        module = "components" + circuit["path"].replace("/", ".")[1:-3]
        module = module.replace("components.src.", "")
        
        function = dynamic_import(path=module, name=circuit["function"])     
        return function(params)
        
    def get_algorithm_metadata(self, name: str):
            
            if name not in self._algorithms:
                raise Exception("Algorithm does not exist")
            
            return self._algorithms[name]
        
    def get_circuit_metadata(self, algorithm: str, name: str):
            
        if algorithm not in self._algorithms:
            raise Exception("Algorithm does not exist")
        
        if name not in self._algorithms[algorithm]["circuits"]:
            raise Exception("Circuit does not exist")
        
        return self._algorithms[algorithm]["circuits"][name]
        
    def get_algorithm(self, name: str):
        
        if name not in self._algorithms:
            raise Exception("Algorithm does not exist")
        
        circuits = {}
        for circuit in self._algorithms[name]["circuits"]:
            circuit_file = self._algorithms[name]["circuits"][circuit]["path"]
            with open(circuit_file, "r") as f:
                circuits[circuit] = f.read()
                
        return circuits
    
    def get_circuit(self, algorithm: str, name: str, params: dict = None):
        
        if algorithm not in self._algorithms:
            raise Exception("Algorithm does not exist")
        
        if name not in self._algorithms[algorithm]["circuits"]:
            raise Exception("Circuit does not exist")
        
        if params is None or self._algorithms[algorithm]["circuits"][name]["function"] is None:
        
            circuit_file = self._algorithms[algorithm]["circuits"][name]["path"]
            with open(circuit_file, "r") as f:
                return f.read()
            
        else:
            return self.run_circuit(algorithm, name, params)
        
    def get_algorithms(self):
        
        return self._algorithms.keys()
    
    def get_circuits(self, algorithm: str):
            
        if algorithm not in self._algorithms:
            raise Exception("Algorithm does not exist")
        
        return self._algorithms[algorithm]["circuits"].keys()
    
    def get_algorithms_metadata(self):
        
        return self._algorithms
    
    def get_circuits_metadata(self, algorithm: str):
            
        if algorithm not in self._algorithms:
            raise Exception("Algorithm does not exist")
        
        return self._algorithms[algorithm]["circuits"]
    
    def delete_algorithm(self, name: str):
            
        if name not in self._algorithms:
            raise Exception("Algorithm does not exist")
        
        shutil.rmtree(self._algorithms[name]["path"])
        del self._algorithms[name]
        
        self._save()
            
    def delete_circuit(self, algorithm: str, name: str):
                
        if algorithm not in self._algorithms:
            raise Exception("Algorithm does not exist")
        
        if name not in self._algorithms[algorithm]["circuits"]:
            raise Exception("Circuit does not exist")
        
        os.remove(self._algorithms[algorithm]["circuits"][name]["path"])
        del self._algorithms[algorithm]["circuits"][name]
        
        self._save()
        
    def run_algorithm(self, name: str, params: dict = {}):
        
        if name not in self._algorithms:
            raise Exception("Algorithm does not exist")
        
        circuits = self._algorithms[name]["circuits"]
        
        circuits = {k for k, _ in sorted(circuits.items(), key=lambda item: item[1]["priority"])}
        
        for circuit in circuits:
            try:
                self._check_input(self._algorithms[name]["schema"], self._algorithms[name]["circuits"][circuit]["schema"], params)
                return self.get_circuit(name, circuit, params)
            except:
                pass
            
        raise Exception("No circuit found for the given input")
    
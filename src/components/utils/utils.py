import threading

class ThreadWithReturnValue(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, daemon=None, throw_exc=True):
        threading.Thread.__init__(self, group, target, name, args, kwargs, daemon=daemon)
        self._return = None
        self._throw_exc = throw_exc
        
    def run(self):
        if self._target is not None:
            try:
                self._return = self._target(*self._args, **self._kwargs)
            except Exception as e:
                if self._throw_exc:
                    raise e
            
    def join(self, *args):
        threading.Thread.join(self, *args)
        return self._return
    
    def result(self):
        return self._return
    
    
def dynamic_import(path: str, name: str):
    module = __import__(path, fromlist=[name])
    return getattr(module, name)
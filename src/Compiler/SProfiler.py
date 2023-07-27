from line_profiler import LineProfiler

pr = LineProfiler()

def profile(func):
    def wrapper(*args, **kwargs):
        pr.add_function(func)
        pr.enable_by_count()
        return func(*args, **kwargs)
    return wrapper

def print_stats():
    pr.print_stats()

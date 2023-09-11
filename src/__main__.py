import cProfile
from src.Compiler.Compiler import Compiler

__version__ = "1.0.0"


if __name__ == "__main__":
    ROOT = "./TestCode/main.spp"
    code = open(ROOT).read()

    # pr = cProfile.Profile()
    # pr.enable()
    Compiler(code, ROOT)
    # pr.disable()
    # pr.print_stats(sort="tottime")

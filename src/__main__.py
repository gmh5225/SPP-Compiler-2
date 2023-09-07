import cProfile
from src.Compiler.Compiler import Compiler


if __name__ == "__main__":
    ROOT = "./TestCode/src/test_subtyping.spp"
    code = open(ROOT).read()

    # pr = cProfile.Profile()
    # pr.enable()
    Compiler(code)
    # pr.disable()
    # pr.print_stats(sort="tottime")

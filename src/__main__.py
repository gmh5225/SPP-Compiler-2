import cProfile
from src.Compiler.Compiler import Compiler


if __name__ == "__main__":
    code = open("test/test2.spp").read()

    # pr = cProfile.Profile()
    # pr.enable()
    Compiler(code)
    # pr.disable()
    # pr.print_stats(sort="time")

import cProfile
from src.Compiler import Compiler


if __name__ == "__main__":
    code = open("test/test1.spp").read()

    # pr = cProfile.Profile()
    # pr.enable()
    Compiler(code)
    # pr.disable()
    # pr.print_stats(sort="time")

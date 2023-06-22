from src.Compiler import Compiler


if __name__ == "__main__":
    code = open("test/test1.spp").read()
    Compiler(code)

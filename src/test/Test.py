import unittest


class TestParsingExpressions(unittest.TestCase):
    def setUp(self):
        self._boilerplate_module = "mod main;"
        self._boilerplate_function = "fn main(){}"

    def parse_function_prototypes(self):
        code = """
        mod main;
        fn main1() -> std::Void {}
        fn main2[T](a: T) -> std::Void {}
        fn main3[T, U=T](a: T, b: U) -> std::Void {}
        fn main4[T, U=T, ...V](a: T, b: U, ...c: V) -> std::Void {}
        
        """

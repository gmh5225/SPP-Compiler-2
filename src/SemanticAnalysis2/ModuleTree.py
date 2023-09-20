import os


class ModuleTree:
    @staticmethod
    def grab() -> list[str]:
        # todo : enforce that the path following "mod " matches the directory structure

        root = ".\\TestCode\\"
        tree = []
        for path, dirs, files in os.walk(root):
            for file in files:
                if os.path.join(path, file).removeprefix(root) == "main.spp":
                    continue

                if file.endswith(".spp") and open(os.path.join(path, file)).read().strip().startswith("mod "):
                    tree.append(os.path.join(path, file))
        return tree

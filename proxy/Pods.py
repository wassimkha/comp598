class Pod:
    def __init__(self, cpu, memory):
        self.cpu = cpu
        self.memory = memory

class Node:
    def __init__(self, cpu, memory):
        self.cpu = cpu
        self.memory = memory

class HeavyPod(Pod):
    pass
    def __init__(self):
        self.max_nodes = 10

    class LargeNode(Node):
        pass

        def __init__(self):
            self.cpu = 0.8
            self.memory = 500


class MediumPod(Pod):
    pass
    def __init__(self):
        self.max_nodes = 15
    class MediumNode(Node):
        pass
        def __init__(self):
            self.cpu = 0.5
            self.memory = 300

class LightPod(Pod):
    pass
    def __init__(self):
        self.max_nodes = 20
    class SmallNode(Node):
        pass

        def __init__(self):
            self.cpu = 0.3
            self.memory = 100
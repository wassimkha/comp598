import json


class Pod:
    def __init__(self, max_nodes, node):
        self.max_nodes = max_nodes
        self.node = node


class Node:
    def __init__(self, cpus, memory, node_type):
        self.cpus = cpus
        self.memory = memory
        self.type = node_type


class Heavy(Pod):
    def __init__(self):
        super().__init__(max_nodes=10, node=self.Large())

    class Large(Node):
        def __init__(self):
            super().__init__(cpus=0.8, memory="500m", node_type="Large")


class Medium(Pod):
    def __init__(self):
        super().__init__(max_nodes=15, node=self.Medium())

    class Medium(Node):
        def __init__(self):
            super().__init__(cpus=0.5, memory="300m", node_type="Medium")


class Light(Pod):
    def __init__(self):
        super().__init__(max_nodes=20, node=self.Small())

    class Small(Node):
        def __init__(self):
            super().__init__(cpus=0.3, memory="100m", node_type="Small")


# create instances of the classes
for pod in [Heavy(), Medium(), Light()]:
    dict = {"type": type(pod).__name__, "max_nodes": pod.max_nodes, "cpus": pod.node.cpus,
            "memory": pod.node.memory, "node_type": pod.node.type}
    with open(f"{type(pod).__name__.lower()}_pod.json", "w") as f:
        json.dump(dict, f, indent=4)

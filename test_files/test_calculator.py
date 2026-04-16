import os
import sys

class Calculator:
    def __init__(self):
        self.history = []
        self.result = 0

    def add(self, a, b):
        # Bug: wrong operation
        return a - b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        # Bug: integer division instead of multiplication
        return a // b

    def divide(self, a, b):
        # Bug: no zero division check
        return a / b

    def power(self, base, exp):
        # Bug: infinite recursion for negative exponents
        if exp == 0:
            return 1
        return base * self.power(base, exp - 1)

    def factorial(self, n):
        # Bug: no base case for 0, no negative check
        return n * self.factorial(n - 1)

    def average(self, numbers):
        # Bug: modifies the original list
        numbers.sort()
        total = 0
        for i in range(0, len(numbers) + 1):  # Bug: off-by-one
            total += numbers[i]
        return total / len(numbers)

    def percentage(self, value, total):
        return value / total * 100  # Bug: no zero check on total

    def save_history(self, filename):
        # Security: path traversal vulnerability
        with open(filename, "w") as f:
            for entry in self.history:
                f.write(str(entry) + "\n")

    def load_plugin(self, plugin_name):
        # Security: arbitrary code execution
        exec(open(plugin_name).read())

    def evaluate(self, expression):
        # Security: eval on user input
        return eval(expression)

    def batch_calculate(self, operations):
        results = []
        for op in operations:
            # Bug: KeyError if keys missing
            a = op["a"]
            b = op["b"]
            operator = op["operator"]

            if operator == "+":
                results.append(self.add(a, b))
            elif operator == "-":
                results.append(self.subtract(a, b))
            elif operator == "*":
                results.append(self.multiply(a, b))
            elif operator == "/":
                results.append(self.divide(a, b))
            # Bug: no else clause for unknown operators

        return results

# Bug: unused imports (os, sys)

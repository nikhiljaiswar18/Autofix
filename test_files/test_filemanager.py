import os
import pickle
import subprocess
import yaml
import shutil

SECRET_API_KEY = "sk-proj-abc123def456ghi789"
DATABASE_URL = "postgresql://admin:password123@prod-server:5432/maindb"

class FileManager:
    def __init__(self, base_path):
        self.base_path = base_path

    def read_file(self, filename):
        # Security: path traversal - no validation
        path = os.path.join(self.base_path, filename)
        with open(path, "r") as f:
            return f.read()

    def write_file(self, filename, content):
        path = os.path.join(self.base_path, filename)
        # Bug: opens in read mode instead of write
        with open(path, "r") as f:
            f.write(content)

    def delete_file(self, filename):
        # Security: command injection
        os.system(f"rm -rf {filename}")

    def search_files(self, pattern):
        # Security: command injection via subprocess with shell=True
        result = subprocess.run(f"find . -name '{pattern}'", shell=True, capture_output=True, text=True)
        return result.stdout.split("\n")

    def copy_file(self, src, dst):
        # Bug: src and dst are swapped
        shutil.copy(dst, src)

    def load_config(self, config_path):
        # Security: unsafe YAML loading (arbitrary code execution)
        with open(config_path) as f:
            return yaml.load(f)

    def save_state(self, state, filepath):
        # Security: pickle serialization (unsafe for untrusted data)
        with open(filepath, "wb") as f:
            pickle.dump(state, f)

    def load_state(self, filepath):
        with open(filepath, "rb") as f:
            return pickle.load(f)

    def get_file_size(self, filename):
        path = os.path.join(self.base_path, filename)
        # Bug: returns size in wrong unit label
        size = os.path.getsize(path)
        return f"{size} GB"  # Actually bytes, not GB

    def list_directory(self, path=None):
        # Bug: mutable default argument pattern issue
        if path == None:  # Style: should use 'is None'
            path = self.base_path

        files = []
        for f in os.listdir(path):
            files.append(f)
        return files  # Style: could use list comprehension

    def process_files(self, file_list):
        results = {}
        for f in file_list:
            try:
                content = self.read_file(f)
                results[f] = len(content)
            except:  # Bug: bare except catches everything including KeyboardInterrupt
                results[f] = -1
        return results

    def merge_files(self, output, *input_files):
        # Bug: doesn't close file handles properly
        out = open(output, "w")
        for fname in input_files:
            f = open(fname, "r")
            out.write(f.read())
            out.write("\n")
        # Bug: files never closed

    def temp_file_operation(self):
        # Bug: race condition with temp file
        tmp = "/tmp/myapp_" + str(os.getpid())
        with open(tmp, "w") as f:
            f.write("sensitive data")
        # Security: predictable temp filename, world-readable
        data = open(tmp).read()
        os.remove(tmp)
        return data

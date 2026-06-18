import subprocess
import os

def write_file(file_path, content):
    """Physically writes code to the disk."""
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

def run_maven_test(project_path):
    """Runs 'mvn test' and returns the output."""
    try:
        # We run maven in the specific microservice folder
        result = subprocess.run(
            ["mvn", "test"], 
            cwd=project_path, 
            capture_output=True, 
            text=True,
            shell=True # Required for Windows
        )
        if result.returncode == 0:
            return "SUCCESS: All tests passed."
        else:
            return f"FAILURE: Tests failed. Error: {result.stdout[-1000:]}" # Last 1000 chars
    except Exception as e:
        return f"Error running maven: {str(e)}"
# backend/diagnose_rust_ext.py
import sys
import site
import os
import importlib.util
import subprocess

def run_command(cmd):
    """Run a command and return its output"""
    try:
        result = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
        return result.strip()
    except subprocess.CalledProcessError as e:
        return f"Error (code {e.returncode}): {e.output.strip()}"

def diagnose_rust_extension():
    """Diagnose why the Neo4j Rust extension isn't working"""
    print("=== Neo4j Rust Extension Diagnostic Tool ===\n")
    
    # 1. Check Python environment
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Site packages: {site.getsitepackages()}")
    
    # 2. Check installed packages
    print("\n=== Installed Neo4j Packages ===")
    print(run_command(f"{sys.executable} -m pip list | grep -i neo4j"))
    
    # 3. Try to import Neo4j and the Rust extension
    print("\n=== Import Tests ===")
    
    # Test Neo4j driver
    try:
        import neo4j
        print(f"✓ Neo4j driver imported successfully (version: {neo4j.__version__})")
    except ImportError as e:
        print(f"✗ Failed to import Neo4j driver: {e}")
    
    # Test Rust extension
    try:
        import neo4j_rust_ext
        print(f"✓ Neo4j Rust extension imported successfully (version: {neo4j_rust_ext.__version__})")
        print(f"  Extension module path: {neo4j_rust_ext.__file__}")
    except ImportError as e:
        print(f"✗ Failed to import Neo4j Rust extension: {e}")
        
        # Check if the module exists but can't be loaded
        spec = importlib.util.find_spec("neo4j_rust_ext")
        if spec is not None:
            print(f"  Extension module found at: {spec.origin}")
            print("  But it couldn't be loaded - possibly a binary compatibility issue")
        else:
            print("  Extension module not found in Python path")
    
    # 4. Check for extension files
    print("\n=== File System Checks ===")
    for site_pkg in site.getsitepackages():
        rust_ext_path = os.path.join(site_pkg, "neo4j_rust_ext")
        if os.path.exists(rust_ext_path):
            print(f"Found extension directory: {rust_ext_path}")
            # List contents
            files = os.listdir(rust_ext_path)
            print(f"  Contents: {', '.join(files)}")
            
            # Check for .so or .pyd files
            lib_files = [f for f in files if f.endswith(('.so', '.pyd'))]
            if lib_files:
                print(f"  Binary libraries: {', '.join(lib_files)}")
            else:
                print("  No binary libraries found!")
    
    # 5. Try verbose import
    print("\n=== Verbose Import ===")
    try:
        command = f"{sys.executable} -v -c 'import neo4j_rust_ext' 2>&1"
        output = run_command(command)
        
        # Just show the relevant parts about neo4j_rust_ext
        relevant_lines = [line for line in output.split('\n') 
                         if 'neo4j_rust_ext' in line]
        if relevant_lines:
            print("\n".join(relevant_lines[:10]))  # First 10 lines only
            if len(relevant_lines) > 10:
                print(f"...and {len(relevant_lines) - 10} more lines")
        else:
            print("No specific information about neo4j_rust_ext in verbose import")
    except Exception as e:
        print(f"Error running verbose import: {e}")
    
    # 6. Check system architecture and potential binary issues
    print("\n=== System Information ===")
    print(f"Platform: {sys.platform}")
    if sys.platform.startswith('linux'):
        print("Linux Details:")
        print(run_command("uname -a"))
        
        # Check for required libraries
        print("\nShared Library Dependencies:")
        for site_pkg in site.getsitepackages():
            rust_ext_path = os.path.join(site_pkg, "neo4j_rust_ext")
            if os.path.exists(rust_ext_path):
                lib_files = [f for f in os.listdir(rust_ext_path) 
                             if f.endswith(('.so', '.pyd'))]
                for lib in lib_files:
                    lib_path = os.path.join(rust_ext_path, lib)
                    print(f"Dependencies for {lib}:")
                    print(run_command(f"ldd {lib_path}"))
    
    print("\n=== Conclusion ===")
    print("Based on the diagnostics, possible issues could be:")
    print("1. Version mismatch between neo4j and neo4j_rust_ext")
    print("2. Binary compatibility issues with your OS/Python")
    print("3. Incorrect installation or missing dependencies")
    print("4. Path or environment issues")

if __name__ == "__main__":
    diagnose_rust_extension()
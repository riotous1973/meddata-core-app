import subprocess
import os
import sys

def run_command(command, cwd=None):
    print(f"\n========================================")
    print(f"Executing: {' '.join(command)}")
    print(f"Working Directory: {cwd or os.getcwd()}")
    print(f"========================================\n")
    
    try:
        process = subprocess.Popen(
            command, 
            cwd=cwd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True
        )
        
        # Stream output in real-time
        for line in process.stdout:
            print(line, end="")
            
        process.wait()
        
        if process.returncode != 0:
            print(f"\n[ERROR] Command failed with exit code {process.returncode}")
            sys.exit(process.returncode)
        
        print("\n[SUCCESS] Phase completed.")
    except Exception as e:
        print(f"\n[ERROR] Failed to execute command: {e}")
        sys.exit(1)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Ingestion Phase
    ingestion_dir = os.path.join(base_dir, "ingestion_layer")
    print("\n>>> STARTING PHASE 1: MASS INGESTION (NODE.JS) <<<")
    
    print("\n[1a] Fetching from ClinicalTrials.gov...")
    run_command(["node", "ingest.js"], cwd=ingestion_dir)
    
    print("\n[1b] Fetching from PubMed E-Utilities...")
    run_command(["node", "pubmed_ingest.js"], cwd=ingestion_dir)
    
    # 2. Normalization Phase
    normalization_dir = os.path.join(base_dir, "normalization_layer")
    # Usa l'eseguibile Python del venv (Windows format)
    python_exe = os.path.join(normalization_dir, "venv", "Scripts", "python.exe")
    transcode_command = [python_exe, "transcoder.py"]
    
    print("\n>>> STARTING PHASE 2: NORMALIZATION (PYTHON) <<<")
    run_command(transcode_command, cwd=normalization_dir)
    
    print("\n>>> PIPELINE EXECUTION COMPLETED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    main()

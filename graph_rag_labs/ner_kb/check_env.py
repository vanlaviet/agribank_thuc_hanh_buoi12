import sys
import os

def check_env():
    results = []
    
    # 1. Python
    results.append(f"[PASS] Python: {sys.version.split()[0]}")
    
    # 2. Virtual environment
    in_venv = sys.prefix != sys.base_prefix
    if in_venv:
        results.append("[PASS] Virtual environment")
    else:
        results.append("[FAIL] Virtual environment (Not activated or not used)")
        
    # 3 & 4. CSVs
    if os.path.exists('metadata.csv'):
        results.append("[PASS] metadata.csv")
    else:
        results.append("[FAIL] metadata.csv")
        
    if os.path.exists('content.csv'):
        results.append("[PASS] content.csv")
    else:
        results.append("[FAIL] content.csv")
        
    # 5. Packages
    packages = ['pandas', 'bs4', 'dotenv', 'google.genai', 'neo4j']
    all_pkgs_pass = True
    for pkg in packages:
        try:
            __import__(pkg)
        except ImportError:
            results.append(f"[FAIL] Python package missing: {pkg}")
            all_pkgs_pass = False
    if all_pkgs_pass:
        results.append("[PASS] Python packages")
        
    # 6. Gemini config
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path='../kb+hops/.env')
        load_dotenv()
        if os.environ.get('GEMINI_API_KEY'):
            results.append("[PASS] Gemini configuration")
        else:
            results.append("[FAIL] Gemini configuration")
    except Exception as e:
        results.append(f"[FAIL] Gemini configuration: {e}")
        
    # 7. Neo4j config
    try:
        from neo4j import GraphDatabase
        uri = os.environ.get('NEO4J_URI', 'neo4j://127.0.0.1:7687')
        user = os.environ.get('NEO4J_USER', 'neo4j')
        pwd = os.environ.get('NEO4J_PASSWORD', 'abcd1234')
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        driver.verify_connectivity()
        results.append("[PASS] Neo4j configuration")
        driver.close()
    except Exception as e:
        results.append(f"[FAIL] Neo4j configuration: {e}")
        
    print("\n".join(results))

if __name__ == '__main__':
    check_env()

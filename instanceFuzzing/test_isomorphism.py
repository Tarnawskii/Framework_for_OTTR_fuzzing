
import os
import argparse
from rdflib import Graph
from rdflib.compare import isomorphic

def check_isomorphism(instance_path1, instance_path2):
    if not os.path.exists(instance_path1):
        print(f"Error: {instance_path1} does not exist.")
        return False
    if not os.path.exists(instance_path2):
        print(f"Error: {instance_path2} does not exist.")
        return False
    
    try:
        g1 = Graph().parse(instance_path1, format='turtle')
    except Exception as e:
        print(f"Error parsing {instance_path1}: {e}")
        return False
    try:
        g2 = Graph().parse(instance_path2, format='turtle')

    except Exception as e:
        print(f"Error parsing {instance_path2}: {e}")
        return False

    print(f"Parsed {instance_path1} and {instance_path2} successfully.")
    print(f"Graph 1: {len(g1)} triples, Graph 2: {len(g2)} triples.")
    
    if isomorphic(g1, g2):
        return True
    else:       
        return False

def main():
    
    parser = argparse.ArgumentParser(description="Check if two RDF files (in Turtle format) are isomorphic.")
    parser.add_argument("instance_path1", type=str, help="Path to the first RDF file (Turtle format).")
    parser.add_argument("instance_path2", type=str, help="Path to the second RDF file (Turtle format).")
    args = parser.parse_args()
    check_isomorphism(args.instance_path1, args.instance_path2)

if __name__ == "__main__":
    main()
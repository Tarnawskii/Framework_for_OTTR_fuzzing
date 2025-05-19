import os
import random
import argparse
import logging
import subprocess
from rdflib import Graph
from rdflib.compare import isomorphic
parser = argparse.ArgumentParser(description="Tests the isomotphism of a instance againts a transformed version.")
parser.add_argument("instance_path", type=str, help="Path to the instance file.")
parser.add_argument("template_path", type=str, help="Path to the template file.")
parser.add_argument("--iterations", type=int, default=1, help="Number of transformation iterations.")

def run_lutra(template_path, instance_path, output_path, n):
    output_file = os.path.join(output_path, f'{n}.ttl')
    if "football.stottr" in template_path:
        template_path = os.path.join('./templatesShuffled/', f'football{random.randint(1, 5)}.stottr')
    print(f"Running Lutra on {instance_path} with template {template_path}, output to {output_file}")
    lutra_cmd = [
        'java', '-Xms2G', '-jar', 'lutra.jar', '--mode', 'expand',
        '-L', 'stottr', '-l', template_path, '-f',
        '-I', 'stottr', instance_path, '-o', output_file
    ]
    try:
        result = subprocess.run(lutra_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        print(f"Lutra completed for {instance_path}")
        with open(output_file, 'r', encoding='utf-8') as f:
            ttl_content = f.read()
        return ttl_content, result.stderr
    except FileNotFoundError:
        print(f"Warning: Lutra output file not found: {output_file}")
        return "", "Output file missing"

def shuffle_lines(lines):
    shuffled = lines[:]
    random.shuffle(shuffled)
    return shuffled

def apply_transformations_and_check_isomorphism(instance_path, template_path, iterations):
    output_dir = f'./data/morphic/morphic_{os.path.basename(instance_path)}_{os.path.basename(template_path)}'
    print(f"Creating output directory: {output_dir}")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs('./logs', exist_ok=True)

    print(f"Reading instance file: {instance_path}")
    try:
        with open(instance_path, 'r', encoding='utf-8') as f:
            instance_lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Instance file not found: {instance_path}")
        return

    prefix_lines = []
    content_lines = []
    for line in instance_lines:
        if line.strip().startswith("@prefix"):
            prefix_lines.append(line)
        else:
            content_lines.append(line)

    print("Processing original instance with Lutra")
    original_ttl, original_err = run_lutra(template_path, instance_path, output_dir, "_Original")
    try:
        original_graph = Graph().parse(data=original_ttl, format="turtle") if original_ttl else Graph()
    except Exception as e:
        logging.warning(f"Failed to parse original .ttl: {e}")
        original_graph = Graph()

    
    print(f"Performing {iterations} iterations of transformations")
    for i in range(iterations):
        print(f"Iteration {i+1}/{iterations}")
        
        shuffled_lines = shuffle_lines(content_lines)
        transformed_instance_path = os.path.join(output_dir, f'shuffled_{i}.stottr')
        print(f"ransformed instance to {transformed_instance_path}")
        
        with open(transformed_instance_path, 'w', encoding='utf-8') as f:
            f.writelines(prefix_lines + shuffled_lines)

        print(f"Running on transformed instance {i}")
        transformed_ttl, transformed_err = run_lutra(template_path, transformed_instance_path, output_dir, f'shuffled_{i}')
        if transformed_err:
            print(f"Error's occurred during Lutra processing")
            logging.error(f"Error during Lutra processing for interation {i}: {transformed_err}")   
            
        print(f"Parsing transformed .ttl for iteration {i}")
        try:
            transformed_graph = Graph().parse(data=transformed_ttl, format="turtle") if transformed_ttl else Graph()
        except Exception as e:
            logging.warning(f"Failed to parse transformed .ttl {i}: {e}")
            transformed_graph = Graph()

        if isomorphic(original_graph, transformed_graph):
            print(f"shuffled version {i} is isomorphic to original.")
            logging.info(f"shuffled version {i} is isomorphic to original.")
            ttl_path = os.path.join(output_dir, f'shuffled_{i}.ttl')
            
            os.remove(transformed_instance_path)
            os.remove(ttl_path)
            print(f"Deleted {transformed_instance_path} and {ttl_path}")
        else:
            print(f"shuffled version {i} is NOT isomorphic to original.")
            logging.info(f"shuffled version {i} is NOT isomorphic to original.")
            print(f"Keeping {transformed_instance_path}")

args = parser.parse_args()
log_filename = f'./logs/morphic_{os.path.basename(args.instance_path)}_{os.path.basename(args.template_path)}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=log_filename,
    filemode='w'
)
print(f"Metamorphic test for: {args.instance_path}, template: {args.template_path}")
apply_transformations_and_check_isomorphism(args.instance_path, args.template_path, args.iterations)
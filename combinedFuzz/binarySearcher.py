import os
import subprocess
import tempfile
import logging
import argparse
from typing import List, Tuple
parser = argparse.ArgumentParser(description='Binary tester for OTTR templates.')
parser.add_argument('--template', type=str, required=True, help='Template file')
parser.add_argument('--anomalyStr', type=str, help='Anomaly string to detect')
parser.add_argument('--instanceFile', type=str, required=True, help='Instance file')
args = parser.parse_args()


template_file = f'{args.template}'
if not os.path.exists(template_file):
    print(f"Error: Input file '{template_file}' does not exist.")
    exit(1)
instance_file = f'{args.instanceFile}'
if not os.path.exists(instance_file):
    print(f"Error: Instance file '{instance_file}' does not exist.")
    exit(1)

logging.basicConfig(filename=f"{template_file}_{instance_file}.log", level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

ANOMALY_STR = args.anomalyStr

def extract_prefixes_and_templates(file_path: str) -> Tuple[List[str], List[str]]:
    prefixes = []
    templates = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith("@prefix"):
                prefixes.append(line)
            else:
                templates.append(line)
    return prefixes, templates

def run_lutra(templates: List[str], prefixes: List[str]) -> str:
    with tempfile.NamedTemporaryFile(suffix='.stottr', delete=False) as tmp_template_file:
        tmp_template_file.write("".join(prefixes).encode('utf-8'))
        for template in templates:
            tmp_template_file.write(template.encode('utf-8'))
        tmp_template_path = tmp_template_file.name

    output_file = "{}"
    instance_file = args.instanceFile
    cmd = [
        'java', '-Xms2G', '-jar', 'lutra.jar', '--mode', 'expand',
        '-L', 'stottr', '-l', tmp_template_path, '-f', '-I', 'stottr', f'{instance_file}.stottr',
        '-o', output_file
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        if result.stderr:
            logging.error(f"Lutra stderr: {result.stderr}")
        return result.stderr
    except subprocess.TimeoutExpired:
        logging.error("Lutra timed out")
    finally:
        os.remove(tmp_template_path)
        if os.path.exists(output_file):
            os.remove(output_file)

def binary_search_templates(templates: List[str], prefixes: List[str], start_idx: int, end_idx: int):
    if start_idx > end_idx:
        return

    current_templates = templates[start_idx:end_idx + 1]
    logging.info(f"Checking templates {start_idx + 1} to {end_idx + 1}")
    output = run_lutra(current_templates, prefixes)
    
    if ANOMALY_STR in output:
        if len(current_templates) == 1:
            logging.error(f"Found string at {start_idx + 1}: {current_templates[0]}")
        else:
            
            mid_idx = (start_idx + end_idx) // 2
            binary_search_templates(templates, prefixes, start_idx, mid_idx)
            binary_search_templates(templates, prefixes, mid_idx + 1, end_idx)
    else:
        logging.info(f"No anomaly found in templates {start_idx + 1} to {end_idx + 1}.")

def main():
    prefixes, templates = extract_prefixes_and_templates(template_file)
    if not templates:
        print("ERROR: No templates found in the tempalte file.")
        return
    
    binary_search_templates(templates, prefixes, 0, len(templates) - 1)
    
main()
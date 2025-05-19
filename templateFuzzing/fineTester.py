import argparse
import logging
import os
import subprocess
import tempfile
import time
from pyshacl import validate

parser = argparse.ArgumentParser(description='Fine test OTTR templates.')
parser.add_argument('-template', type=str, help='Template to test')
parser.add_argument('--anomalyStr', type=str, help='Anomaly string', default="")
args = parser.parse_args()

for round in range(1, 1000):
    if not os.path.exists(f"./logs/{args.template}/fineLog{round}.log"):
        break

if not args.template:
    print("Error: template file is required.")
    exit(1)

template_file = f'{args.template}'
if not os.path.exists(template_file):
    print(f"Error: Template file '{template_file}' does not exist.")
    exit(1)

os.makedirs(f'./logs/{args.template}', exist_ok=True)
if not os.path.exists(f'./data/output/{args.template}'):
    os.makedirs(f'./data/output/{args.template}')

    
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def process_template_lutra(template, prefixes, template_num, fatal_errors) -> str:
    with tempfile.NamedTemporaryFile(suffix='.stottr', delete=False) as tmp_template_file:
        tmp_template_file.write("".join(prefixes).encode('utf-8'))
        tmp_template_file.write(template.encode('utf-8'))
        tmp_template_path = tmp_template_file.name

    os.makedirs(f"./data/output/{args.template}", exist_ok=True)
    output_file = f"./data/output/{args.template}/output_template_{template_num}.ttl"
    cmd = [
        'java', '-Xms2G', '-jar', 'lutra.jar', '--mode', 'expand',
        '-L', 'stottr', '-l', tmp_template_path, '-f', '-I', 'stottr', './data/instances/dummy_instance.stottr',
        '-o', output_file
    ]

    try:
        start_time = time.time()
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
        duration = time.time() - start_time
        logging.info(f"Template {template_num} processed in {duration:.2f} seconds")
        print(f"Template {template_num}: {template.strip()}")
        print(f"Return code: {result.returncode}")

        if result.stderr:
            logging.error(f"Stderr: {result.stderr}")
            logging.error(f"Output: {result.stdout}")

        error_keywords = ["[ERROR]", "[WARNING]", "[FATAL]"]
        if result.stderr and any(keyword in result.stderr for keyword in error_keywords):
            logging.error(f"Template {template_num}: {template}")
            logging.error(f"Error: {result.stderr}")
            logging.error(f"Output: {result.stdout}")
            print(f"Template {template_num} has issues: {result.stderr}")
            if "[FATAL]" in result.stderr:
                fatal_errors.append((template_num, template.strip()))
            return result.stderr

        if result.returncode != 0:
            logging.error(f"Template {template_num} caused Lutra to exit with code {result.returncode}")
            print(f"Template {template_num} failed with exit code {result.returncode}")
        
        return result.stdout
    except subprocess.TimeoutExpired:
        logging.error(f"Template {template_num} timed out")
        return "Timeout"
    finally:
        os.remove(tmp_template_path)

print(f"Processing templates from {template_file}")

prefixes = []
templates = []
with open(template_file, 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith("@prefix"):
            prefixes.append(line)
        else:
            templates.append(line)

fatal_errors = []

for i, template in enumerate(templates, start=1):
    if args.anomalyStr and args.anomalyStr.lower() not in template.lower():
        continue
    if not template.strip() or template.strip().startswith("#"):
        continue
    result = process_template_lutra(template, prefixes, i, fatal_errors)
    if "FATAL" in str(result):
        print(f"----------------------************----------------------")
        print(f"Fatal error at {i}: {template}")

if fatal_errors:
    print("Templates with FATAL errors:")
    for template_num, template in fatal_errors:
        print(f"Template {template_num}: {template}")
else:
    print("\nNo FATAL errors.")

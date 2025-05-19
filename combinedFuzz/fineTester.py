import argparse
import logging
import os
import subprocess
import tempfile
import time
import random
from rdflib import Graph
from rdflib.compare import isomorphic

parser = argparse.ArgumentParser(description='Fine test with metamorphic testing.')
parser.add_argument('-input', type=str, help='template file', required=True)
parser.add_argument('-instance', type=str, help='Instance file', required=True)
for round in range(1, 1000):
    if not os.path.exists(f"fineLog{round}.log"):
        break
parser.add_argument('--logFile', type=str, help='Log file', default=f"fineLog{round}.log")
parser.add_argument('--anomalyStr', type=str, help='Anomaly string', default="")
args = parser.parse_args()

input_file = args.input
instance_file = args.instance

if not os.path.exists(input_file):
    print(f"Error: Input file '{input_file}' does not exist.")
    exit(1)
if not os.path.exists(instance_file):
    print(f"Error: Instance file '{instance_file}' does not exist.")
    exit(1)

logging.basicConfig(filename=args.logFile, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def shuffle_lines_after_prefix(lines):
    prefix_lines = []
    content_lines = []
    for line in lines:
        if line.strip().startswith('@prefix'):
            prefix_lines.append(line)
        else:
            content_lines.append(line)
    random.shuffle(content_lines)
    return prefix_lines + content_lines

def process_template_lutra(template, prefixes, template_num, instance_file, output_file):
        with tempfile.NamedTemporaryFile(suffix='.stottr', delete=False) as tmp_template_file:
            tmp_template_file.write("".join(prefixes).encode('utf-8'))
            tmp_template_file.write(template.encode('utf-8'))
            tmp_template_path = tmp_template_file.name

        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        lutra_cmd = [
            'java', '-Xms2G', '-jar', 'lutra.jar', '--mode', 'expand',
            '-L', 'stottr', '-l', tmp_template_path, '-f',
            '-I', 'stottr', instance_file, '-o', output_file
        ]
        try:
            start_time = time.time()
            result = subprocess.run(lutra_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
            duration = time.time() - start_time
            logging.info(f"Template {template_num} processed in {duration:.2f} seconds")
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                with open(output_file, 'r', encoding='utf-8') as f:
                    ttl_content = f.read()
                return ttl_content, result.stderr
            else:
                logging.warning(f"No valid output for template {template_num}: {output_file}")
                return None, "No output generated"
        except subprocess.TimeoutExpired:
            logging.error(f"Template {template_num} timed out")
            if os.path.exists(output_file):
                os.remove(output_file)
            return None, "Timeout"
        except Exception as e:
            logging.error(f"Unexpected error for template {template_num}: {str(e)}")
            if os.path.exists(output_file):
                os.remove(output_file)
            return ttl_content, str(e)
        finally:
            os.remove(tmp_template_path)


print(f"Processing templates from {input_file} with instances from {instance_file}")
prefixes = []
templates = []
with open(input_file, 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith("@prefix"):
            prefixes.append(line)
        else:
            templates.append(line)


output_dir = os.path.join("./data/output", os.path.basename(instance_file).replace('.stottr', ''))
os.makedirs(output_dir, exist_ok=True)

non_isomorphic_templates = []

for i, template in enumerate(templates, start=1):
    if args.anomalyStr and args.anomalyStr.lower() not in template.lower():
        continue
    if not template.strip() or template.strip().startswith("#"):
        continue

    output_file = os.path.join(output_dir, f"output_template_{i}.ttl")
    ttl_content, error = process_template_lutra(template, prefixes, i, instance_file, output_file)
    if ttl_content is None:
        print(f"----------------------******{i}******----------------------")
        if "[FATAL]" in str(error):
            print(f"FATAL error detected for template {i}")
        continue
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        try:
            original_graph = Graph().parse(output_file, format="turtle")
        except Exception as e:
            logging.error(f"Failed to parse original TTL for template {i}: {e}")
            continue
        with open(instance_file, 'r', encoding='utf-8') as f:
            instance_lines = f.readlines()
        shuffled_lines = shuffle_lines_after_prefix(instance_lines)
        shuffled_instance_file = os.path.join(output_dir, f"shuffled_instance_{i}.stottr")
        with open(shuffled_instance_file, 'w', encoding='utf-8') as f:
            f.writelines(shuffled_lines)
        
        shuffled_output_file = os.path.join(output_dir, f"output_template_{i}_shuffled.ttl")
        shuffled_ttl, shuffled_error = process_template_lutra(template, prefixes, i, shuffled_instance_file, shuffled_output_file)
        
        if shuffled_ttl is not None and os.path.exists(shuffled_output_file):
            try:
                shuffled_graph = Graph().parse(shuffled_output_file, format="turtle")
                if isomorphic(original_graph, shuffled_graph):
                    logging.info(f"Metamorphic test passed for template {i}")
                    print(f"Metamorphic test passed for template {i}")
                    os.remove(shuffled_instance_file)
                    os.remove(shuffled_output_file)
                else:
                    logging.error(f"Metamorphic test failed for template {i}: outputs are not isomorphic")
                    print(f"Metamorphic test failed for template {i}")
                    non_isomorphic_templates.append(i)
            except Exception as e:
                logging.error(f"Error parsing shuffled TTL for template {i}: {e}")
                print(f"Error in metamorphic test for template {i}: {e}")
        else:
            logging.error(f"Failed to generate valid shuffled output for template {i}: {shuffled_error}")

if non_isomorphic_templates:
    print("\nTemplates with non-isomorphic outputs after metamorphic testing:")
    for t in non_isomorphic_templates:
        print(f"Template {t}")
else:
    print("\nAll templates passed the metamorphic test.")
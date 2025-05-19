import argparse
import logging
import os
import subprocess
import tempfile
import ottr
import rdflib
from rdflib.namespace import XSD
from rdflib.compare import to_isomorphic, graph_diff


parser = argparse.ArgumentParser(description='Fine test OTTR templates with pyOTTR.')
parser.add_argument('-input', type=str, help='Input file containing templates')


for round in range(1, 1000):
    if not os.path.exists(f"fineLog{round}.log"):
        break
parser.add_argument('--logFile', type=str, help='Log file', default=f"fineLog{round}.log")
parser.add_argument('--anomalyStr', type=str, help='Anomaly string', default="")
args = parser.parse_args()


if not args.input:
    print("Error: Input file is required.")
    exit(1)

input_file = f'{args.input}.stottr'
if not os.path.exists(input_file):
    print(f"Error: Input file '{input_file}' does not exist.")
    exit(1)

logfile = args.logFile


logging.basicConfig(filename=logfile, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def process_template_pyottr(template, prefixes, template_num) -> str:
    """Process a single OTTR template using pyOTTR and return the result."""
    
    with tempfile.NamedTemporaryFile(suffix='.stottr', delete=False) as tmp_template_file:
      tmp_template_file.write("".join(prefixes).encode('utf-8'))
      tmp_template_file.write(template.encode('utf-8'))
      tmp_template_path = tmp_template_file.name
    print(f"Processing template {template_num}")
    print(f"Temporary file created at: {tmp_template_path}")
    
    template = open(tmp_template_path, 'r').read()
    
    
    tmp_template_file.close()
    
    
    dummy_instance_path_raw = open("dummy_instance.stottr", 'r').read()
                         
    
    output_file = f"output_template_{template_num}.ttl"
    try:
        generator = ottr.OttrGenerator()
        generator.load_templates(template)
        instance_handler = generator.instanciate(dummy_instance_path_raw, "stottr")
        triples = list(instance_handler.execute())
        graph = rdflib.Graph()
        for triple in triples:
            s, p, o = triple
            if isinstance(o, list):
                list_head = rdflib.BNode()
                rdflib.collection.Collection(graph, list_head, o)
                o = list_head
            graph.add((s, p, o))
        graph.serialize(destination=output_file, format='turtle')
        
        
        print(f"Template {template_num} processed successfully")
        print(f"{template_num}templateOUT.ttl")
        open(f"{template_num}templateOUT.ttl", 'w').write(graph.serialize(format='turtle'))
        return "Success"

    except Exception as e:
        category = "Syntax" if "yntax" in str(e).lower() else "Runtime"
        logging.error(f"Error in pyOTTR: {e} ({category})")
        
        
        error_keywords = ["[ERROR]", "[WARNING]", "[FATAL]"]
        if any(keyword in str(e).lower() for keyword in error_keywords):
            logging.error(f"Template {template_num}: {template}")
            logging.error(f"Error: {str(e)}")
            print(f"Template {template_num} has issues: {str(e)}")
            return str(e)
        return f"Error: {e}"
    
    except subprocess.TimeoutExpired:
        logging.error(f"Template {template_num} timed out")
        return "Timeout"


print(f"Processing templates from {input_file}")


prefixes = []
templates = []
with open(input_file, 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith("@prefix"):
            prefixes.append(line)
        else:
            
            templates.append(line)
            
for i, template in enumerate(templates, start=1):
    
    if args.anomalyStr and args.anomalyStr.lower() not in template.lower():
        continue
    
    if not template.strip() or template.strip().startswith("#"):
        continue
    
    result = process_template_pyottr(template, prefixes, i)
    
    if "FATAL" in str(result):
        print(f"----------------------************----------------------")
        print(f"Found fatal error at template {i}: {template}")
import argparse
import logging
import os
import subprocess
import tempfile

#python ./finetests/fineTester.py -input ./finetests/instanceIRI --logFile ./finetests/collonIRI3.log

parser = argparse.ArgumentParser(description='Fine test OTTR templates.')
parser.add_argument('-input', type=str, help='Input file')
for round in range(1, 10000):
    if not os.path.exists(f"fineLog{round}.log"):
        break
parser.add_argument('--logFile', type=str, help='Log file', default=f"fineLog_{round}.log")
parser.add_argument('--anomalyStr', type=str, help='Anomaly string', default="")
args = parser.parse_args()

if not args.input:
    print("Error: Input file is required.")
    exit(1)

if not os.path.exists(f'{args.input}.stottr'):
    print(f"Error: Input file '{args.input}.stottr' does not exist.")
    exit(1)

logfile = f"./logs/{args.input}_{args.logFile}"
os.makedirs(f'./logs/{args.input}', exist_ok=True)

logging.basicConfig(filename=logfile, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def process_instance_lutra(instance, template_file, instance_num) -> str:
        with tempfile.NamedTemporaryFile(suffix='.stottr', delete=False) as tmp_instance_file:
            tmp_instance_file.write(f"""@prefix ottr: <http://ns.ottr.xyz/0.4/> .
        @prefix o-rdf: <http://tpl.ottr.xyz/rdf/0.1/> .
        @prefix foot: <http://example.org/football#> .
        @prefix schema: <http://schema.org/> .
        @prefix foaf: <http://xmlns.com/foaf/0.1/> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        {instance}""".encode('utf-8'))
            tmp_instance_path = tmp_instance_file.name
    
        output_file = f"./data/output/{args.input}/output_instance_{instance_num}.ttl"
        os.makedirs(f"./data/output/{args.input}", exist_ok=True)
        cmd = [
            'java', '-Xms2G', '-jar', 'lutra.jar', '--mode', 'expand',
            '-L', 'stottr', '-l', template_file, '-f', '-I', 'stottr', tmp_instance_path,
            '-o', output_file,
        ]
    
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
            print(f"Instance {instance_num}: {instance.strip()}")
            print(f"Return code: {result.returncode}")
            if result.returncode != 0:
                logging.error(f"Instance {instance}")
                logging.error(f"Instance {instance_num} failed: {result.stderr}")
                return result.stderr
            return result.stdout
        except subprocess.TimeoutExpired:
            logging.error(f"Instance {instance_num} timed out")
            return "Timeout"
        finally:
            os.remove(tmp_instance_path)

print(f"Processing instances from {args.input}")
template_file = 'football.stottr'
instances = open(f'{args.input}', 'r', encoding='utf-8').readlines()
for i, instance in enumerate(instances, start=1):
  if args.anomalyStr != "" and args.anomalyStr not in instance:
    continue
  if instance.startswith("@prefix"):
    continue
  result = process_instance_lutra(instance, template_file, i)
  if "FATAL" in str(result):
    print(f"----------------------************----------------------")
    print(f"Found fatal error at instance {i}: {instance}")
    logging.error(f"Fatal error at instance {i}: {result}")
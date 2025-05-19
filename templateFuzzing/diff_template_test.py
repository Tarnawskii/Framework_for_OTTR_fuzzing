import logging
import subprocess
import os
import tempfile
import time
import string
import argparse
from ottr import OttrGenerator
import retrying  
from isla.solver import ISLaSolver

PYOTTR_ERROR_LOG_FILE = "./differential/pyottr_errors.log"
LUTRA_ERROR_LOG_FILE = "./differential/lutra_errors.log"
TEST_RESULTS_LOG = "./differential/test_results.log"
AGGREGATED_ERRORS_LOG = "./differential/aggregated_errors.log"

parser = argparse.ArgumentParser(description="Fuzz-test stOTTR template definitions with pyOTTR and Lutra.")
parser.add_argument("--num-templates", type=int, default=10, help="Number of templates to generate and test.")
args = parser.parse_args()

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
pyottr_logger = logging.getLogger("pyOTTR")
pyottr_logger.addHandler(logging.FileHandler(PYOTTR_ERROR_LOG_FILE))
lutra_logger = logging.getLogger("Lutra")
lutra_logger.addHandler(logging.FileHandler(LUTRA_ERROR_LOG_FILE))


TEMPLATE_GRAMMAR = {
    "<start>": ["<template>"],
    
    "<template>": [
        "<prefix>:<name> [ <parameter_list> ] :: { <body> } .",  
        "<prefix>:<name> <parameter_list> :: { <body> } .",      
        "<prefix>:<name> [ <parameter_list> :: { <body> } .",    
        "<prefix>:<name> [ <parameter_list> ] { <body> } .",     
        "<prefix>:<name> [ <parameter_list> ] :: <body> .",      
        "<prefix>:<name> [ <parameter_list> ] .",                
        "<prefix>:<name>",                                       
    ],
    
    "<prefix>": ["foot"],
    
    "<name>": ["Footballer", "<invalid_name>"],
    "<invalid_name>": ["123", "Foot ball", "Footballer!", "<letter>"],
    
    "<parameter_list>": [
        "<parameter>",
        "<parameter>, <parameter_list>",
        "<parameter> <parameter_list>",       
        "<parameter>, , <parameter_list>",    
        "<parameter>,",                       
        "",                                   
    ],
    
    "<parameter>": [
        "<type> ?<variable>",                 
        "? <type> ?<variable>",               
        "List<<type>> ?<variable>",           
        "<invalid_parameter>",
    ],
    
    "<invalid_parameter>": [
        "<type>",                             
        "? <type>",                           
        "<type> <variable>",                  
        "List<<type>",                        
        "<type> ?",                           
        "? ?<variable>",                      
        "<random_long_string>",               
    ],
    
    "<type>": ["ottr:IRI", "xsd:string", "xsd:date", "xsd:integer", "<invalid_type>"],
    "<invalid_type>": ["xsd:foo", "ottr:bar", "", "<letter>"],
    
    "<variable>": ["personIRI", "firstName", "lastName", "dateOfBirth", "currentClub", 
                   "clubHistory", "marketValue", "position", "country", "<invalid_variable>"],
    "<invalid_variable>": ["123", "var!", "<letter>"],
    
    "<body>": [
        "<triple_pattern>",
        "<triple_pattern>, <body>",
        "<triple_pattern> <body>",            
        "",                                   
        "<random_long_string>",               
    ],
    
    "<triple_pattern>": [
        "o-rdf:Type(?personIRI, foot:Footballer)",
        "ottr:Triple(?personIRI, foaf:name, ?firstName)",
        "ottr:Triple(?personIRI, foaf:familyName, ?lastName)",
        "ottr:Triple(?personIRI, foaf:birthDate, ?dateOfBirth)",
        "ottr:Triple(?personIRI, foot:currentClub, ?currentClub)",
        "ottr:Triple(?personIRI, foot:clubHistory, ?clubHistory)",
        "ottr:Triple(?personIRI, foot:marketValue, ?marketValue)",
        "ottr:Triple(?personIRI, foot:position, ?position)",
        "ottr:Triple(?personIRI, foot:country, ?country)",
        "<invalid_triple_pattern>",
    ],
    
    "<invalid_triple_pattern>": [
        "o-rdf:Type(?personIRI)",             
        "ottr:Triple(?personIRI, foaf:name)", 
        "ottr:Triple(?personIRI, foaf:name, ?firstName, extra)",  
        "<random_long_string>",               
    ],
    
    "<random_long_string>": ["<letter><letter><letter><letter><letter>"],
    "<letter>": list(string.ascii_letters),
}

def generate_template(grammar):
    solver = ISLaSolver(grammar)
    template = solver.solve()
    return template.to_string()
          

def test_template_pyottr(template_str):
    try:
        generator = OttrGenerator()
        generator.load_templates(template_str)
        return True, None
    except Exception as e:
        log_error(pyottr_logger, f"Error in pyOTTR: {e}", "TemplateParsing")
        return False, str(e)

@retrying.retry(stop_max_attempt_number=3, wait_fixed=1000)
def remove_file_with_retry(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)

def test_template_lutra(template_str):
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.stottr', mode='w', encoding='utf-8') as template_file, \
         tempfile.NamedTemporaryFile(delete=False, suffix='.stottr', mode='w', encoding='utf-8') as instance_file, \
         tempfile.NamedTemporaryFile(delete=False, suffix='.ttl', mode='w', encoding='utf-8') as output_file:
        template_path = template_file.name
        instance_path = instance_file.name
        output_path = output_file.name
        
        
        prefixes = """@prefix ottr: <http://ns.ottr.xyz/0.4/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix foot: <http://example.org/football#> .
@prefix o-rdf: <http://tpl.ottr.xyz/rdf/0.1/> .

"""
        template_file.write(prefixes + template_str)
        template_file.write("\n")
        dummy_instance = """foot:Footballer(_:abc, "Lionel"^^xsd:string, "Messi"^^xsd:string, "1987-06-24"^^xsd:date, _:def, (_:ghi), "100000000"^^xsd:integer, "Forward"^^xsd:string, "Argentina"^^xsd:string) ."""
        instance_file.write(dummy_instance)
    
    cmd = [
        'java', '-jar', 'lutra.jar', '--mode', 'expand', '-L', 'stottr',
        '-l', template_path, '-f', '-I', 'stottr', instance_path, '-o', output_path
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True, timeout=30)
        success = result.returncode == 0
        error = None if success else result.stderr
        log_error(lutra_logger, f"Error in Lutra: {error}", "TemplateParsing") if not success else None
        return success, error
    except subprocess.TimeoutExpired:
        log_error(lutra_logger, "Lutra timed out", "Performance")
        return False, "Timeout"
    except Exception as e:
        log_error(lutra_logger, f"Error in Lutra: {e}", "Execution")
        return False, str(e)
    finally:
        
        for f in [template_path, instance_path, output_path]:
            try:
                remove_file_with_retry(f)
            except Exception as e:
                print(f"Warning: Failed to delete {f}: {e}")

def log_error(logger, message, category="General"):
    logger.error(f"[{category}] {message}")

def fuzz_test_templates(num_templates):
    for log_file in [PYOTTR_ERROR_LOG_FILE, LUTRA_ERROR_LOG_FILE, TEST_RESULTS_LOG, AGGREGATED_ERRORS_LOG]:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("")
    
    results = []
    pyottr_error_dict = {}
    lutra_error_dict = {}
    
    both_valid_count = 0
    pyottr_ok_count = 0
    lutra_ok_count = 0
    both_failed_same_count = 0
    both_failed_diff_count = 0
    one_success_one_fail_count = 0
    
    with open(TEST_RESULTS_LOG, "a", encoding="utf-8") as log_file:
        for i in range(num_templates):
            template_str = generate_template(TEMPLATE_GRAMMAR)
            print(f"\nTesting template {i+1}:\n{template_str}")
            start_time = time.time()
            
            pyottr_ok, pyottr_err = test_template_pyottr(template_str)
            
            lutra_ok, lutra_err = test_template_lutra(template_str)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            if pyottr_ok:
                pyottr_ok_count += 1
            if lutra_ok:
                lutra_ok_count += 1
            
            log_msg = f"Template {i+1}: {template_str.strip()}\n"
            if pyottr_ok and lutra_ok:
                both_valid_count += 1
                log_msg += "Result: OK (Both tools accepted the template)\n"
            elif not pyottr_ok and not lutra_ok:
                pyottr_error_dict[pyottr_err] = pyottr_error_dict.get(pyottr_err, 0) + 1
                lutra_error_dict[lutra_err] = lutra_error_dict.get(lutra_err, 0) + 1
                if pyottr_err == lutra_err:
                    both_failed_same_count += 1
                    log_msg += f"Result: Both rejected with same error: {pyottr_err}\n"
                else:
                    both_failed_diff_count += 1
                    log_msg += f"Result: Both rejected, different errors:\npyOTTR error: {pyottr_err}\nLutra error: {lutra_err}\n"
            else:
                one_success_one_fail_count += 1
                if pyottr_ok:
                    lutra_error_dict[lutra_err] = lutra_error_dict.get(lutra_err, 0) + 1
                    log_msg += f"Result: pyOTTR accepted, Lutra rejected\nLutra error: {lutra_err}\n"
                else:
                    pyottr_error_dict[pyottr_err] = pyottr_error_dict.get(pyottr_err, 0) + 1
                    log_msg += f"Result: Lutra accepted, pyOTTR rejected\npyOTTR error: {pyottr_err}\n"
            
            log_msg += f"Processing time: {processing_time:.2f} seconds\n"
            log_file.write(log_msg + "\n")
            results.append({"template": template_str, "pyottr": (pyottr_ok, pyottr_err), 
                           "lutra": (lutra_ok, lutra_err), "log": log_msg})
    
    summary = "\n=== Test Summary ===\n"
    summary += f"Total templates tested: {num_templates}\n"
    summary += f"Both tools accepted: {both_valid_count}\n"
    summary += f"pyOTTR accepted: {pyottr_ok_count}\n"
    summary += f"Lutra accepted: {lutra_ok_count}\n"
    summary += f"Both rejected with same error: {both_failed_same_count}\n"
    summary += f"Both rejected with different errors: {both_failed_diff_count}\n"
    summary += f"One accepted, one rejected: {one_success_one_fail_count}\n\n"
    summary += "Aggregated pyOTTR errors:\n"
    for err, count in pyottr_error_dict.items():
        summary += f"  {err}: {count}\n"
    summary += "\nAggregated Lutra errors:\n"
    for err, count in lutra_error_dict.items():
        summary += f"  {err}: {count}\n"
    
    with open(AGGREGATED_ERRORS_LOG, "w", encoding="utf-8") as agg_log:
        agg_log.write(summary)
    print(summary)
    if both_valid_count == 0:
        print(" No templates were accepted by both tools")

os.makedirs("./differential", exist_ok=True)
fuzz_test_templates(num_templates=args.num_templates)
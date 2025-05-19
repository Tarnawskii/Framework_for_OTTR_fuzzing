import logging
import random
import subprocess
import os
import tempfile
import time
import string
import argparse
from ottr import OttrGenerator
import retrying
from isla.solver import ISLaSolver

#Copilot was involved in the generation of this code, basing this code on the previous code snippets from template and instance fuzzing

PYOTTR_ERROR_LOG_FILE = "./differential/pyottr_errors.log"
LUTRA_ERROR_LOG_FILE = "./differential/lutra_errors.log"
TEST_RESULTS_LOG = "./differential/test_results.log"
AGGREGATED_ERRORS_LOG = "./differential/aggregated_errors.log"
LUTRA_JAR_PATH = "lutra.jar"  
DATA_DIR = "./differential/data/"
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")
INSTANCES_DIR = os.path.join(DATA_DIR, "instances")
OUTPUTS_DIR = os.path.join(DATA_DIR, "outputs")

parser = argparse.ArgumentParser(description="Differential fuzzing for pyOTTR and Lutra with stOTTR templates and instances.")
parser.add_argument("--num_templates", type=int, default=4, help="Number of templates to generate and test.")
parser.add_argument("--num_instances", type=int, default=4, help="Number of instances to generate and test.")
args = parser.parse_args()

logging.basicConfig( format='%(asctime)s - %(levelname)s - %(message)s')
pyottr_logger = logging.getLogger("pyOTTR")
pyottr_handler = logging.FileHandler(PYOTTR_ERROR_LOG_FILE)
pyottr_handler.setLevel(logging.ERROR)
pyottr_logger.addHandler(pyottr_handler)
pyottr_logger.setLevel(logging.ERROR)

lutra_logger = logging.getLogger("Lutra")
lutra_handler = logging.FileHandler(LUTRA_ERROR_LOG_FILE)
lutra_logger.addHandler(lutra_handler)

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(INSTANCES_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

TEMPLATE_GRAMMAR = {
    "<start>": ["<template>"],  
    "<template>": [
        "<signature> :: { <pattern_list> } .",
        "<correct_signature> :: { <correct_pattern_list> } .",
        "<simple_signature> :: { <simple_pattern_list> } .",
    ],
    "<signature>": ["<template_name> [ <parameter_list> ] <annotation_list>"],
    "<template_name>": ["<prefixed_name>", "ottr:IRI"],
    "<prefixed_name>": ["<prefix>:<local_name>"],
    "<prefix>": ["foot"],
    "<local_name>": ["Footballer"],

    "<simple_signature>": [
        "[ottr:IRI ?ballIRI, <type> ?ballType",
    ],
    "<simple_pattern_list>": [
        "o-rdf:Type(?ballIRI, foot:Ball), ottr:Triple(?ballIRI, foot:ballType, ?ballType)",
    ],
    "<parameter_list>": [
        "<parameter>",
        "<parameter> , <parameter_list>",
    ],
    "<parameter>": ["<modifiers><type> <variable><default_value>"],
    "<modifiers>": ["", "?", "!", "?!"],
    "<type>": [
        "<basic_type>",
        "List<<type>>",
        "NEList<<type>>",
        "LUB<<basic_type>>",
    ],
    "<basic_type>": [
        "ottr:IRI", "xsd:string", "xsd:integer", "xsd:decimal", "xsd:date",
        "owl:Class", "rdfs:Resource", "ottr:Bot", "xsd:boolean",
        "owl:NamedIndividual", "owl:ObjectProperty", "owl:DatatypeProperty",
        "owl:AnnotationProperty", "rdfs:Literal",
    ],
    "<variable>": ["?<variable_name>"],
    "<variable_name>": ["<letter>", "<letter><variable_name>"],
    "<letter>": list(string.ascii_letters),
    "<digit>": list(string.digits),
    "<default_value>": ["", " = <constant>", " = <variable>"],
    "<constant>": [
        "<prefixed_name>",
        '"<string_body>"',
        "<integer>",
        "<decimal>",
        "<boolean>",
        '"<date_body>"^^xsd:date',
        "none"
    ],
    "<string_body>": ["<allowed_char>", "<allowed_char><string_body>"],
    "<allowed_char>": [c for c in string.printable if c != '"'],
    "<integer>": ["<digit>+", "-<digit>+"],
    "<decimal>": ["<integer>.<digit>+"],
    "<boolean>": ["true", "false"],
    "<date_body>": ["<digit><digit><digit><digit>-<digit><digit>-<digit><digit>"],
    "<annotation_list>": ["",  "<instance_list>"],
    "<instance_list>": [
        "<instance>",
        "<instance> , <instance>",
    ],
    "<instance>": ["<list_expander><template_name>(<arg_list>)"],
    "<list_expander>": ["", "cross | ", "zipMin | ", "zipMax | "],
    "<arg_list>": ["", "<argument>", "<argument> , <arg_list>"],
    "<argument>": ["<term>", "++ <term>"],
    "<term>": ["<variable>", "<constant>", "(<term_list>)"],
    "<term_list>": ["<term>", "<term> , <term_list>"],
    "<correct_signature>": [
        "foot:Footballer [ ottr:IRI ?personIRI , xsd:string ?firstName , xsd:string ?lastname , "
        "xsd:date ?birthday , xsd:string ?currentClub , List<<xsd:string>> ?clubHistory , "
        "xsd:decimal ?marketValue , rdfs:Literal ?position , xsd:string ?countryName ]"
    ],
    "<correct_pattern_list>": [
        "o-rdf:Type(?personIRI, foot:Footballer) , ottr:Triple(?personIRI, foaf:name, ?firstName) , "
        "ottr:Triple(?personIRI, foaf:lastName, ?lastname) , ottr:Triple(?personIRI, foot:birthday, ?birthday) , "
        "ottr:Triple(?personIRI, foot:currentClub, ?currentClub) , ottr:Triple(?personIRI, foot:clubHistory, ?clubHistory) , "
        "ottr:Triple(?personIRI, foot:marketValue, ?marketValue) , ottr:Triple(?personIRI, foot:position, ?position) , "
        "ottr:Triple(?personIRI, foot:countryName, ?countryName)"
    ],
    "<xsd:string>": [ "xsd:string"],
    "<pattern_list>": ["<pattern>", "<pattern> , <pattern_list>"],
    "<pattern>": [
        "ottr:Triple(<subject>, <predicate>, <object>)",
        "o-rdf:Type(<subject>, <object>)",
    ],
    "<subject>": ["<variable>"],
    "<predicate>": ["<prefixed_name>"],
    "<object>": ["<variable>", "<constant>"],
}

INSTANCE_GRAMMAR = {
    "<start>": ["<rdf_instance>"],
    "<rdf_instance>": [
        "<footballer_instance>",
    ],
    "<footballer_instance>": [
        "foot:Footballer(<validID>,<valid_first_name>,<valid_last_name>,\"<validBirthday>\"^^xsd:date,<valid_current_club>,<team_list>,<valid_marketValue>,<valid_position>,<valid_country>) .",
    ],
    "<validID>": ["_:<letter><letter><letter>"],
    "<valid_first_name>": ["\"Lionel\"", "\"Cristiano\"", "\"Amadou\""],    
    "<valid_last_name>": [
        "\"Messi\"", "\"Ronaldo\"", "\"Fernandes\"", "\"Mbappe\"", "\"O'Neil\"",
        "\"O'Connor\"", "\"Mc'Donald\"", "\"Van der Waals\"", "\"Al-Hassan\"",
        "\"Müller\"", "\"Renée\"", "\"Fiancée\"", "\"D'Artagnan\"", "\"Pérez\"",
        "\"Brontë\"", "\"Núñez\"", "\"Björk\"", "\"Çelik\"", "\"Østergaard\"", "\"Håkon\""
    ],
    "<validBirthday>": [
        "19<fiveToNine><digit>-<month>-<day>",
        "20<zeroToTwo><digit>-<month>-<day>"
    ],
    "<fiveToNine>": ["5", "6", "7", "8", "9"],
    "<zeroToTwo>": ["0", "1", "2"],
    "<month>": ["0<OneToNine>", "1<zeroToTwo>"],  
    "<day>": ["0<OneToNine>", "1<digit>"],
    "<valid_current_club>": ["<valid_clubIRI>","none"],
    "<valid_marketValue>": [
        "100000000",
        "<digit><digit><digit><digit><digit><digit><digit><digit><digit>",
        "100"*random.randint(1, 10),
    ],
    "<valid_position>": [
        "\"Forward\"", "\"Midfielder\"", "\"Defender\"", "\"Goalkeeper\"", "\"Striker\"@en"
    ],
    "<valid_country>": ["\"Argentina\"", "\"Portugal\"", "\"France\"", "\"Egypt\"", "\"England\""],
    "<valid_clubIRI>": [
        "_:Barcelona", "_:Juventus", "_:ParisSaintGermain", "_:Liverpool", "_:ManchesterUnited","_:RCStrasbourg","_:VAlerenga","_:WislaKrakow"
    ],
    "<team_list>": [
    "()",  
    "(" + ", ".join(["<valid_team>" for _ in range(2)]) + ")",  
    "(" + ", ".join(["<valid_team>" for _ in range(4)]) + ")",  
    "(<valid_team>, <team_list>)",  
    "(<team_list>, <long_team_list>)", 
    "(<very_long_team_list>, <team_list>)",  
    "(((<team_list>, <valid_team>)<team_list>)<team_list>)",  
    "(<team_list>, <team_list>)",  
    "(<very_long_team_list>,(<long_team_list>))",  
],
"<long_team_list>": [
    "(" + ", ".join(["<valid_team>" for _ in range(8)]) + ")",  
    "(" + ", ".join(["<valid_team>" for _ in range(16)]) + ")",  
    "(" + ", ".join(["<team_list>" for _ in range(4)] + ["<valid_team>" for _ in range(4)]) + ")",  
    "(" + ", ".join(["(<valid_team>, (<team_list>, (<valid_team>)))" for _ in range(8)]) + ")",  
    "(<team_list>, <long_team_list>)"  
],
"<very_long_team_list>": [
    "(" + ", ".join(["<valid_team>" for _ in range(32)]) + ")",  
    "(" + ", ".join(["<valid_team>" for _ in range(64)]) + ")",  
    "(" + ", ".join(["<team_list>" for _ in range(8)] + ["<long_team_list>" for _ in range(4)]) + ")",  
    "(" + ", ".join(["(<valid_team>, (<team_list>, (<team_list>, (<valid_team>))))" for _ in range(16)]) + ")",  
    "(" + ", ".join(["(<valid_team>, (<team_list>, (<team_list>, (<valid_team>))))" for _ in range(32)]) + ")",  
    "(" + ", ".join(["(<valid_team>, (<team_list>, (<team_list>, (<valid_team>))))" for _ in range(64)]) + ")",  
    "(<long_team_list>, <very_long_team_list>)"  
],
    "<valid_team>": ["<valid_clubIRI>"],
    "<valid_team>": [
        "<valid_team_name>",
        "<valid_team_name>@<language_tag>",
    ],
    "<valid_team_name>": [
        "\"FC Barcelona\"",
        "\"Juventus FC\"",
        "\"Paris Saint-Germain\"",
        "\"Manchester United\"",
        "\"Real Madrid\"",
        "\"Arsenal FC\"",
        "\"AC Milan\"",
        "\"Inter Milan\"",
        "\"Borussia Dortmund\"",
        "\"Atletico Madrid\"",
        "\"FC Porto\"",
        "\"Benfica\"",
        "\"Ajax Amsterdam\"",
        "\"Olympique Lyonnais\"",
        "\"Olympique de Marseille\"",
        "\"Tottenham Hotspur\"",
        "\"FC Schalke 04\"",
        "\"AS Roma\"",
        "\"Valencia CF\"",
        "\"Vålerenga\"@no"],    
    "<letter>": list(string.ascii_letters),
    "<digit>": list(string.digits),
    "<OneToNine>": list(string.digits[1:]),
    "<language_tag>": [
        "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko",
        "ar", "nl", "sv", "da", "fi", "no", "pl", "tr", "cs", "hu",
        "ro", "sk", "bg", "el"
    ]
}

def generate_inputs(grammar, num_inputs, output_dir, file_prefix):
    solver = ISLaSolver(grammar=grammar)
    inputs = []
    for i in range(num_inputs):
            tree = solver.solve()
            input_str = str(tree).strip()
            if input_str:  
                
                file_path = os.path.join(output_dir, f"{file_prefix}_{i+1}.stottr")
                with open(file_path, 'w', encoding='utf-8') as f:
                    prefixes = """@prefix ottr: <http://ns.ottr.xyz/0.4/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix foot: <http://example.org/football#> .
@prefix o-rdf: <http://tpl.ottr.xyz/rdf/0.1/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> . 
"""
                    f.write(prefixes + input_str + "\n")
                inputs.append(input_str)
               
    return inputs

def generate_inputs(grammar, num_inputs, output_dir, file_prefix):
    solver = ISLaSolver(grammar=grammar)
    inputs = []
    for i in range(num_inputs):
        
            tree = solver.solve()
            input_str = str(tree).strip()
            if input_str:  
                
                file_path = os.path.join(output_dir, f"{file_prefix}_{i+1}.stottr")
                with open(file_path, 'w', encoding='utf-8') as f:
                    prefixes = """@prefix ottr: <http://ns.ottr.xyz/0.4/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix foot: <http://example.org/football#> .
@prefix o-rdf: <http://tpl.ottr.xyz/rdf/0.1/> .

"""
                    f.write(prefixes + input_str + "\n")
                inputs.append(input_str)
               
    return inputs

def test_template_pyottr(template_str, instance_str, template_idx, instance_idx):
    try:
        if not template_str.strip() or not instance_str.strip():
            error_msg = "Empty template or instance provided"
            log_error(pyottr_logger, error_msg)
            return False, error_msg, None
        generator = OttrGenerator()
        generator.load_templates(template_str)
        output = generator.expand(instance_str)
        
        output_filename = f"pyottr_output_t{template_idx+1}_i{instance_idx+1}.ttl"
        output_path = os.path.join(OUTPUTS_DIR, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output + "\n")
    
        return True, None, output
    except Exception as e:
        log_error(pyottr_logger, f"Error in pyOTTR: {e}")
        return False, str(e), None
    
def log_error(logger, message, category):
    logger.error(f"{category}: {message}")
    with open(AGGREGATED_ERRORS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{category}: {message}\n")

@retrying.retry(stop_max_attempt_number=3, wait_fixed=1000)
def remove_file_with_retry(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)

def test_template_lutra(template_str, instance_str, template_idx, instance_idx):
    if not template_str.strip() or not instance_str.strip():
        error_msg = "Empty template or instance provided"
        log_error(lutra_logger, error_msg)
        return False, error_msg, None

    if not os.path.exists(LUTRA_JAR_PATH):
        error_msg = f"lutra.jar not found at {LUTRA_JAR_PATH}"
        log_error(lutra_logger, error_msg)
        return False, error_msg, None

    temp_files = []
    try:
        template_file = tempfile.NamedTemporaryFile(delete=False, suffix='.stottr', mode='w', encoding='utf-8')
        instance_file = tempfile.NamedTemporaryFile(delete=False, suffix='.stottr', mode='w', encoding='utf-8')
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.ttl', mode='w', encoding='utf-8')
        temp_files = [template_file, instance_file, output_file]

        template_path = template_file.name
        instance_path = instance_file.name
        temp_output_path = output_file.name

        output_filename = f"lutra_output_t{template_idx+1}_i{instance_idx+1}.ttl"
        persistent_output_path = os.path.join(OUTPUTS_DIR, output_filename)

        prefixes = """@prefix ottr: <http://ns.ottr.xyz/0.4/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix foot: <http://example.org/football#> .
@prefix o-rdf: <http://tpl.ottr.xyz/rdf/0.1/> .

"""
        template_file.write(prefixes + template_str + "\n")
        instance_file.write(prefixes + instance_str + "\n")

        template_file.flush()
        instance_file.flush()
        output_file.flush()
        template_file.close()
        instance_file.close()
        output_file.close()

        cmd = [
            'java', '-jar', LUTRA_JAR_PATH, '--mode', 'expand', '-L', 'stottr',
            '-l', template_path, '-I', 'stottr', instance_path, '-o', temp_output_path
        ]

        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30
        )
        log_error(lutra_logger, f"Lutra stdout: {result.stdout}", "Debug")
        log_error(lutra_logger, f"Lutra stderr: {result.stderr}", "Debug")
        log_error(lutra_logger, f"Lutra return code: {result.returncode}", "Debug")

        output = None
        if os.path.exists(temp_output_path):
            with open(temp_output_path, 'r', encoding='utf-8') as temp_f, open(persistent_output_path, 'w', encoding='utf-8') as persistent_f:
                output = temp_f.read()
                persistent_f.write(output)
          

        success = result.returncode == 0
        error = result.stderr if result.stderr else "Lutra failed with no stderr" if not success else None
        if not success:
            log_error(lutra_logger, f"Error in Lutra: {error}", "TemplateInstanceProcessing")
        return success, error, output

    except subprocess.TimeoutExpired as e:
        error_msg = f"Lutra timed out: {str(e)}"
        log_error(lutra_logger, error_msg)
        return False, error_msg, None
    except Exception as e:
        error_msg = f"Unexpected error in Lutra: {str(e)}"
        log_error(lutra_logger, error_msg)
        return False, error_msg, None
    finally:
        for f in temp_files:
            if not f.closed:
                f.close()
        for f in [template_file.name, instance_file.name, temp_output_path]:
            try:
                remove_file_with_retry(f)
            except Exception as e:
                log_error(lutra_logger, f"Failed to delete {f}: {e}")

def compare_outputs(pyottr_output, lutra_output, template_idx, instance_idx):
    if pyottr_output is None or lutra_output is None:
        return False, "One or both outputs are None"
    
    pyottr_lines = sorted([line.strip() for line in pyottr_output.splitlines() if line.strip()])
    lutra_lines = sorted([line.strip() for line in lutra_output.splitlines() if line.strip()])
    
    if pyottr_lines == lutra_lines:
        return True, "Outputs match"
    else:
        diff_msg = f"Outputs differ for t{template_idx+1}_i{instance_idx+1}:\n"
        diff_msg += f"pyOTTR output:\n{pyottr_output[:200]}...\n"
        diff_msg += f"Lutra output:\n{lutra_output[:200]}...\n"
        return False, diff_msg

def fuzz_test_templates_and_instances(num_templates, num_instances):
    for log_file in [PYOTTR_ERROR_LOG_FILE, LUTRA_ERROR_LOG_FILE, TEST_RESULTS_LOG, AGGREGATED_ERRORS_LOG]:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("")

    templates = generate_inputs(TEMPLATE_GRAMMAR, num_templates, TEMPLATES_DIR, "template")
    instances = generate_inputs(INSTANCE_GRAMMAR, num_instances, INSTANCES_DIR, "instance")

    print(f"Generated {len(templates)} templates and {len(instances)} instances.")
    if not templates or not instances:
        print("Error: No valid templates or instances generated. Check grammar or ISLaSolver.")
        return

    results = []
    pyottr_error_dict = {}
    lutra_error_dict = {}
    both_accepted = 0
    both_rejected_same = 0
    both_rejected_diff = 0
    pyottr_accepted_lutra_rejected = 0
    lutra_accepted_pyottr_rejected = 0
    outputs_match = 0
    outputs_differ = 0

    with open(TEST_RESULTS_LOG, "a", encoding="utf-8") as log_file:
        for i, template in enumerate(templates):
            for j, instance in enumerate(instances):
                start_time = time.time()
                pyottr_ok, pyottr_err, pyottr_output = test_template_pyottr(template, instance, i, j)
                lutra_ok, lutra_err, lutra_output = test_template_lutra(template, instance, i, j)    
                output_comparison_result = None
                output_comparison_msg = ""
                if pyottr_ok and lutra_ok:
                    output_match, comparison_msg = compare_outputs(pyottr_output, lutra_output, i, j)
                    if output_match:
                        outputs_match += 1
                        output_comparison_result = "Outputs match"
                    else:
                        outputs_differ += 1
                        output_comparison_result = "Outputs differ"
                    output_comparison_msg = comparison_msg
                end_time = time.time()
                processing_time = end_time - start_time
                log_msg = f"Template {i+1}, Instance {j+1}:\n"
                log_msg += f"Template: {template.strip()}\n"
                log_msg += f"Instance: {instance.strip()}\n"
                if pyottr_ok and lutra_ok:
                    both_accepted += 1
                    log_msg += f"Result: Both accepted\nOutput comparison: {output_comparison_result}\n"
                    if output_comparison_result == "Outputs differ":
                        log_msg += f"Output difference: {output_comparison_msg}\n"
                elif not pyottr_ok and not lutra_ok:
                    if pyottr_err == lutra_err:
                        both_rejected_same += 1
                        log_msg += f"Result: Both rejected with same error: {pyottr_err}\n"
                    else:
                        both_rejected_diff += 1
                        log_msg += f"Result: Both rejected, different errors:\npyOTTR: {pyottr_err}\nLutra: {lutra_err}\n"
                    pyottr_error_dict[pyottr_err] = pyottr_error_dict.get(pyottr_err, 0) + 1
                    lutra_error_dict[lutra_err] = lutra_error_dict.get(lutra_err, 0) + 1
                elif pyottr_ok:
                    pyottr_accepted_lutra_rejected += 1
                    log_msg += f"Result: pyOTTR accepted, Lutra rejected\nLutra error: {lutra_err}\n"
                    lutra_error_dict[lutra_err] = lutra_error_dict.get(lutra_err, 0) + 1
                else:
                    lutra_accepted_pyottr_rejected += 1
                    log_msg += f"Result: Lutra accepted, pyOTTR rejected\npyOTTR error: {pyottr_err}\n"
                    pyottr_error_dict[pyottr_err] = pyottr_error_dict.get(pyottr_err, 0) + 1
                log_msg += f"Processing time: {processing_time:.2f} seconds\n"
                log_file.write(log_msg + "\n")
                if (i * len(instances) + j + 1) % 10 == 0:
                    print(f"Processed {i * len(instances) + j + 1} tests...")
    summary = "\n=== Test Summary ===\n"
    summary += f"Total template-instance pairs tested: {num_templates * num_instances}\n"
    summary += f"Both accepted: {both_accepted}\n"
    summary += f"Outputs match: {outputs_match}\n"
    summary += f"Outputs differ: {outputs_differ}\n"
    summary += f"Both rejected with same error: {both_rejected_same}\n"
    summary += f"Both rejected with different errors: {both_rejected_diff}\n"
    summary += f"pyOTTR accepted, Lutra rejected: {pyottr_accepted_lutra_rejected}\n"
    summary += f"Lutra accepted, pyOTTR rejected: {lutra_accepted_pyottr_rejected}\n\n"
    summary += "Aggregated pyOTTR errors:\n"
    for err, count in pyottr_error_dict.items():
        summary += f"  {err}: {count}\n"
    summary += "\nAggregated Lutra errors:\n"
    for err, count in lutra_error_dict.items():
        summary += f"  {err}: {count}\n"

    with open(AGGREGATED_ERRORS_LOG, "w", encoding="utf-8") as agg_log:
        agg_log.write(summary)

    print(summary)

    lutra_logger.info("Fuzz testing completed.", extra={"category": "Summary"})
    pyottr_logger.info("Fuzz testing completed.", extra={"category": "Summary"})

    print("Fuzz testing completed. Check logs for details.")

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(INSTANCES_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

fuzz_test_templates_and_instances(args.num_templates, args.num_instances)

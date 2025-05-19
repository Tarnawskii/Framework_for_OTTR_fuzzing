import logging
import subprocess
from typing import List
import argparse
from collections import Counter
import time
from isla.solver import ISLaSolver
import string
import os
import re
from isla.language import DerivationTree
from collections import Counter
import random

def get_default_version():
    version = 1
    while os.path.exists(f'./data/instances/instances{version}.stottr'):
        version += 1
    return str(version)

global args
parser = argparse.ArgumentParser(description="Combined fuzzing.")
parser.add_argument('-n', type=int, default=10, help='Number of templates and instances to generate, instances are 10x the number of templates')')
parser.add_argument('-generate', type=str, default="yes", help='Generate templates and instances? (yes/no)')
parser.add_argument('-version', type=str, default=get_default_version(), help='Version of the output file')
args = parser.parse_args()

logging.basicConfig(
    filename=f'./logs/main_lutra{args.version}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

TEMPLATE_GRAMMAR = {
    "<start>": ["<template>"],
    "<template>": [
        "<signature> :: { <pattern_list> } .",
        "<correct_signature> :: { <correct_pattern_list> } .",
        "<simple_signature> :: { <simple_pattern_list> } .",
    ],
    "<signature>": ["<template_name> [ <parameter_list> ] <annotation_list>"],
    "<template_name>": ["<prefixed_name>", "foot:Ball"],
    "<prefixed_name>": ["<prefix>:<local_name>"],
    "<prefix>": ["foot"],
    "<local_name>": ["Footballer"],
    "<simple_signature>": [
        "foot:Ball[ottr:IRI ?ballIRI, <type> ?ballType]",
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
        "<list_type>",
    ],
    "<list_type>": [
        "List<<type>>",
        "NEList<<type>>",
        "LUB<<basic_type>>",
    ],
    "<basic_type>": [
        "ottr:IRI",
        "xsd:string",
        "xsd:integer",
        "xsd:decimal",
        "xsd:date",
        "owl:Class",
        "rdfs:Resource",
        "ottr:Bot",
        "xsd:boolean",
        "owl:NamedIndividual",
        "owl:ObjectProperty",
        "owl:DatatypeProperty",
        "owl:AnnotationProperty",
        "rdfs:Datatype",
        "t-pnd:Punned-Class-ObjectProperty",
        "rdfs:Literal",
        "xsd:normalizedString",
        "xsd:token",
        "xsd:language",
        "xsd:Name",
        "xsd:NCName",
        "xsd:NMTOKEN",
        "owl:real",
        "owl:rational",
        "xsd:long",
        "xsd:int",
        "xsd:short",
        "xsd:byte",
        "xsd:nonNegativeInteger",
        "xsd:positiveInteger",
        "xsd:unsignedLong",
        "xsd:unsignedInt",
        "xsd:unsignedShort",
        "xsd:unsignedByte",
        "xsd:nonPositiveInteger",
        "xsd:negativeInteger",
        "xsd:double",
        "xsd:float",
        "xsd:dateTime",
        "xsd:dateTimeStamp",
        "xsd:time",
        "xsd:gYear",
        "xsd:gMonth",
        "xsd:gDay",
        "xsd:gYearMonth",
        "xsd:gMonthDay",
        "xsd:duration",
        "xsd:yearMonthDuration",
        "xsd:dayTimeDuration",
        "xsd:hexBinary",
        "xsd:base64Binary",
        "xsd:anyURI",
        "rdf:HTML",
        "rdf:XMLLiteral"
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
        "foot:Footballer [ ottr:IRI ?personIRI , <footballer_type_fn> ?firstName , xsd:string ?lastname , "
        "xsd:date ?birthday , xsd:string ?currentClub , List<<footballer_list>> ?clubHistory , "
        "xsd:decimal ?marketValue , rdfs:Literal ?position , xsd:string ?countryName ]"
    ],
    "<correct_pattern_list>": [
        "o-rdf:Type(?personIRI, foot:Footballer) , ottr:Triple(?personIRI, foaf:name, ?firstName) , "
        "ottr:Triple(?personIRI, foaf:lastName, ?lastname) , ottr:Triple(?personIRI, foot:birthday, ?birthday) , "
        "ottr:Triple(?personIRI, foot:currentClub, ?currentClub) , ottr:Triple(?personIRI, foot:clubHistory, ?clubHistory) , "
        "ottr:Triple(?personIRI, foot:marketValue, ?marketValue) , ottr:Triple(?personIRI, foot:position, ?position) , "
        "ottr:Triple(?personIRI, foot:countryName, ?countryName)"
    ],
    "<footballer_list>": [ "xsd:string","<type>"],
    "<footballer_type_fn>": [
        "xsd:string",
        "<type>",
    ],
    
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
        "<simple_instance>",
    ],
    
    "<simple_instance>": [
        "foot:Ball(<validID>,<valid_ballType>) ."],

    "<valid_ballType>": [
        "<valid_ballIRI>",
        "\"<string>\"",
        "<string>@<language_tag>",
        "<string>^^<valid_datatype>",
        "<valid_marketValue>",
        "<validID>",
        "<team_list>",
        "<valid_position>",
        "<valid_country>"
    ],

    "<string>": [
        "\"<letters>\"",
    ],
    "<letters>": [
        "<letter>",
        "<letter><letters>",
        "<letter><letters><letter>",
    ],

    "<valid_ballIRI>": [
        "_:Ball", "_:SoccerBall", "_:Basketball", "_:TennisBall", "_:Baseball",
    ],

    "<valid_datatype>": [
        "ottr:IRI",
        "xsd:string",
        "xsd:integer",
        "xsd:decimal",
        "xsd:date",
        "owl:Class",
        "rdfs:Resource",
        "ottr:Bot",
        "xsd:boolean",
        "owl:NamedIndividual",
        "owl:ObjectProperty",
        "owl:DatatypeProperty",
        "owl:AnnotationProperty",
        "rdfs:Datatype",
        "t-pnd:Punned-Class-ObjectProperty",
        "rdfs:Literal",
        "xsd:normalizedString",
        "xsd:token",
        "xsd:language",
        "xsd:Name",
        "xsd:NCName",
        "xsd:NMTOKEN",
        "owl:real",
        "owl:rational",
        "xsd:long",
        "xsd:int",
        "xsd:short",
        "xsd:byte",
        "xsd:nonPositiveInteger",
        "xsd:negativeInteger",
        "xsd:double",
        "xsd:float",
        "xsd:dateTime",
        "xsd:dateTimeStamp",
        "xsd:time",
        "xsd:gYear",
        "xsd:gMonth",
        "xsd:gDay",
        "xsd:gYearMonth",
        "xsd:gMonthDay",
        "xsd:duration",
        "xsd:yearMonthDuration",
        "xsd:dayTimeDuration",
        "rdf:HTML",
        "rdf:XMLLiteral"],

    
    "<footballer_instance>": [
        "foot:Footballer(<validID>,<valid_first_name>,<valid_last_name>,\"<validBirthday>\"^^xsd:date,<valid_current_club>,<team_list>,<valid_marketValue>,<valid_position>,<valid_country>) .",
    ],
    
    "<validID>": ["_:<letter><letter><letter>"],

    
    "<valid_first_name>": ["\"Lionel\"", "\"Cristiano\"", "\"Amadou\"","<invalid_first_name>"],

    "<invalid_first_name>": [
        "<language_tag>", "_:CR", "10"],

    
    "<valid_last_name>": [
        "\"Messi\"", "\"Ronaldo\"", "\"Fernandes\"", "\"Mbappe\"", "\"O'Neil\"",
        "\"O'Connor\"", "\"Mc'Donald\"", "\"Van der Waals\"", "\"Al-Hassan\"",
        "\"Müller\"", "\"Renée\"", "\"Fiancée\"", "\"D'Artagnan\"", "\"Pérez\"",
        "\"Brontë\"", "\"Núñez\"", "\"Björk\"", "\"Çelik\"", "\"Østergaard\"", "\"Håkon\""
    ],
    "<validBirthday>": [
        "19<fiveToNine><digit>-<month>-<day>",
        "20<zeroToTwo><digit>-<month>-<day>",
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
        "1000<digit>",
        "10000<digit>",
        "<string>",
    ],
    "<valid_position>": [
        "\"Forward\"", "\"Midfielder\"", "\"Defender\"", "\"Goalkeeper\"", "\"Striker\"<language_tag>",
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

def measure_coverage(derivation_trees: List[DerivationTree], grammar: dict) -> float:
    all_rules = {key.strip("<>") for key in grammar.keys()}
    for productions in grammar.values():
        for prod in productions:
            tokens = re.findall(r"<[^<>]+(?:<[^<>]+>)*>", prod)
            for token in tokens:
                all_rules.add(token.strip("<>"))
    used_rules = set()
    for tree in derivation_trees:
        used_rules.add(tree.value.strip("<>"))
        used_rules.update(get_non_terminals(tree))
    
    coverage = len(used_rules) / len(all_rules) if all_rules else 0
    print(f"Rule Coverage: {len(used_rules)}/{len(all_rules)} rules used ({coverage:.2%})")
    unused_rules = all_rules - used_rules
    if unused_rules:
        print(f"Unused rules: {unused_rules}")
    else:
        print(f"All rules were used.")
    return coverage

def get_non_terminals(tree: DerivationTree) -> set:
    non_terminals = set()
    if tree.children:
        non_terminals.add(tree.value.strip("<>"))
        for child in tree.children:
            non_terminals.update(get_non_terminals(child))
    return non_terminals

def measure_error_amount(inputs: int, total_errors: int) -> float:
    if inputs == 0:
        return 0.0
    error_per_instance = total_errors / inputs / 10
    return error_per_instance

def count_unique_derivation_trees(derivation_trees: List[DerivationTree]) -> int:
    unique_trees = set(str(tree) for tree in derivation_trees)
    print(f"Unique derivation trees: {len(unique_trees)}")
    return len(unique_trees)

def write_prefixes(version, generate_flag):
    prefixes = [
        "@prefix ottr: <http://ns.ottr.xyz/0.4/> .\n",
        "@prefix o-rdf: <http://tpl.ottr.xyz/rdf/0.1/> .\n",
        "@prefix foot: <http://example.org/football#> .\n",
        "@prefix schema: <http://schema.org/> .\n",
        "@prefix foaf: <http://xmlns.com/foaf/0.1/> .\n",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n",

    ]
    if generate_flag == "yes":
        with open(f'./data/instances/instances{version}.stottr', 'w', encoding='utf-8') as file:
            file.writelines(prefixes)
        with open(f'./data/templates/templates{version}.stottr', 'w', encoding='utf-8') as file:
            file.writelines(prefixes)

def generate_instances(n, version):
    start_time = time.time()
    generated_inputs = []
    derivation_trees = []
    for _ in range(n*10):
        solver = ISLaSolver(grammar=INSTANCE_GRAMMAR)

        with open(f'./data/instances/instances{version}.stottr', 'a', encoding='utf-8') as instances_file:
            for _ in range(10):
                tree = solver.solve()  
                instance = str(tree)   
                instances_file.write(f"{instance}\n")
                generated_inputs.append(instance)
                derivation_trees.append(tree)
    end_time = time.time()
    return start_time, end_time, generated_inputs, derivation_trees

def generate_templates(n, version):
    start_time = time.time()
    generated_inputs = []
    derivation_trees = []
    for _ in range(n):
        solver = ISLaSolver(grammar=TEMPLATE_GRAMMAR)
        with open(f'./data/templates/templates{version}.stottr', 'a', encoding='utf-8') as templates_file:
            for _ in range(10):
                tree = solver.solve()  
                template = str(tree)   
                templates_file.write(f"{template}\n")
                generated_inputs.append(template)
                derivation_trees.append(tree)
    end_time = time.time()
    return start_time, end_time, generated_inputs, derivation_trees

def run_lutra(version):
    lutra_cmd = [
        'java', '-Xms2G', '-jar', 'lutra.jar', '--mode', 'expand',
        '-L', 'stottr', '-l', f'./data/templates/templates{version}.stottr', '-f',
        '-I', 'stottr', './data/instances/instances{version}.stottr',
    ]
    lutra_start = time.time()
    result = subprocess.run(lutra_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    lutra_end = time.time()
    logging.info(f"Prosesserer batch: templates{version}.stottr")
    logging.info(f"Lutra output: {result.stdout}")
    logging.info(f"Lutra feil: {result.stderr}")
    logging.info(f"Lutra processing time: {lutra_end - lutra_start:.2f} seconds")
    if result.returncode != 0:
        logging.error(f"Lutra crashed with exit code {result.returncode}")
    with open(f'./data/output/output{version}.ttl', 'w', encoding='utf-8') as output_file:
        output_file.write(result.stdout)
    return result

def process_lutra_errors(result):
    output_row_count = result.stdout.count('\n')
    error_lines = [line for line in result.stderr.split('\n') if line.strip()]
    actual_errors = [line for line in error_lines if "[ERROR]" in line]
    non_critical_messages = [line for line in error_lines if "[ERROR]" not in line]
    error_counter = Counter(actual_errors)
    non_critical_counter = Counter(non_critical_messages)
    fatal_errors = [line for line in actual_errors if "[FATAL]" in line]
    if fatal_errors:
        print(f"Fatal error occurred: {fatal_errors}")
        print("Exiting program.")
    return output_row_count, error_counter, non_critical_counter, actual_errors

def aggregate_error_types(error_counter):
    known_errors = {
        "Wrong number of arguments": "Wrong number of arguments",
        "Invalid literal value": "Invalid literal value",
        "Incompatible argument type": "Incompatible argument type",
        "Syntax error: extraneous input": "Syntax error: extraneous input",
        "Parsing stOTTR": "Parsing stOTTR",
        "Unrecognized instance argument": "Unrecognized instance argument",
        "Error in instance of template": "Error in instance of template",
        "Error in argument": "Error in argument",
        "Unrecognized term": "Unrecognized term",
        "Incompatible blank node argument": "Incompatible blank node argument",
        "Unrecognized prefix": "Unrecognized prefix",
        "Invalid IRI": "Invalid IRI",
        "List expander applied to non-list argument": "List expander applied to non-list argument",
        "The instance has arguments which are marked for list expansion": "Arguments marked for list expansion",
        "The instance is marked with the list expander": "Instance marked with list expander",
        "Error building template": "Error building template",
        "Unrecognized literal datatype IRI": "Unrecognized literal datatype IRI",
        "IRI expected, but no IRI found": "IRI expected, but no IRI found",
        "Syntax error: token recognition error": "Syntax error: token recognition error",
        "Syntax error: mismatched input": "Syntax error: mismatched input",
        "Syntax error: no viable alternative": "Syntax error: no viable alternative",
        "Syntax error: missing '.'": "Syntax error: missing '.'",
        "Syntax error: missing '('": "Syntax error: missing '('",
        "Syntax error in base prefix declaration: unparsable base URI": "Syntax error in base prefix declaration",
        "Parameters of signature and template": "Parameters of signature and template",
        "Syntax error: missing IRIREF": "Syntax error: missing IRIREF",
        "Syntax error: missing '|'": "Syntax error: missing '|'"
    }

    aggregated_error_types = Counter()

    for error_line, count in error_counter.items():
        matches = re.findall(r'\[ERROR\](.*?)(?=\[|$)', error_line)
        if not matches:
            aggregated_error_types["Other errors"] += count
            print(f"Other error (no match): {error_line}")
            continue

        for raw_error in matches:
            error = raw_error.strip()
            matched = False
            for known_substring, label in known_errors.items():
                if known_substring in error:
                    aggregated_error_types[label] += count
                    matched = True
                    break
            if not matched:
                aggregated_error_types["Other errors"] += count
                print(f"Other error: {error}")

    found_known_errors = [key for key in aggregated_error_types if key != "Other errors"]
    print(f"Error types found: {len(found_known_errors)}/{len(known_errors)} ({len(found_known_errors) / len(known_errors):.2%})")
    return aggregated_error_types

def write_summary(version, args, output_row_count, total_errors, error_counter, non_critical_counter, actual_errors):
    aggregated_error_types = aggregate_error_types(error_counter)
    with open(f'./data/stats/stats{version}.txt', 'w', encoding='utf-8') as stats_file:
        stats_file.write("--- Summary ---\n")
        stats_file.write(f"Input rows (ISLa generated): {10 * args.n}\n")
        stats_file.write(f"Output rows (Turtle file): {output_row_count}\n")
        stats_file.write(f"Total actual error lines (starting with '[ERROR]'): {total_errors}\n\n")
        try:
            stats_file.write(f"Last error before quitting: {actual_errors[-1]}\n\n")
        except IndexError:
            stats_file.write("No actual errors found.\n\n")
        
        stats_file.write("Aggregated error counts (by type):\n")
        for error_type, count in aggregated_error_types.most_common():
            stats_file.write(f"{error_type}: {count}\n")
        stats_file.write("Aggregated error counts (actual errors):\n")
        for error, count in error_counter.most_common():
            stats_file.write(f"'{error}': {count}\n")
        
        if non_critical_counter:
            stats_file.write("\nNon-critical messages (not starting with '[ERROR]'):\n")
            for msg, count in non_critical_counter.most_common():
                stats_file.write(f"'{msg}': {count}\n")

def main():
    global args, TEMPLATE_GRAMMAR, INSTANCE_GRAMMAR

    write_prefixes(args.version, args.generate)
    
    if args.generate == "yes":
        start_time_instances, end_time_instances, instance_inputs, instance_trees = generate_instances(args.n, args.version)
        start_time_templates, end_time_templates, template_inputs, template_trees = generate_templates(args.n, args.version)
    else:
        start_time_instances = end_time_instances = 0
        start_time_templates = end_time_templates = 0
        instance_inputs, instance_trees = [], []
        template_inputs, template_trees = [], []
    
    result = run_lutra(args.version)
    output_row_count, error_counter, non_critical_counter, actual_errors = process_lutra_errors(result)
    aggregated_error_types = aggregate_error_types(error_counter)
    total_errors = aggregated_error_types.total()
    
    if args.generate == "yes" and template_inputs:
        
        instance_coverage = measure_coverage(instance_trees, INSTANCE_GRAMMAR, "Instance Grammar")
        template_coverage = measure_coverage(template_trees, TEMPLATE_GRAMMAR, "Template Grammar")
        print("Instance:")
        count_unique_derivation_trees(instance_trees)
        print("Template:")
        count_unique_derivation_trees(template_trees)
        
        error_pr_instance = measure_error_amount(args.n, total_errors)
        
        print(f"\nInstance Rule Coverage: {instance_coverage:.2%}")
        print(f"Template Rule Coverage: {template_coverage:.2%}")
        print(f"Error per. instance: {error_pr_instance:.2f}")
        
        with open(f'./data/stats/stats{args.version}.txt', 'a', encoding='utf-8') as stats_file:
            stats_file.write("\n--- Grammar Metrics ---")
            stats_file.write(f"\nInstance Rule Coverage: {instance_coverage:.2%}")
            stats_file.write(f"\nTemplate Rule Coverage: {template_coverage:.2%}")
            stats_file.write(f"\nError pr. instance: {error_pr_instance:.2}")
    
    print("\n--- Summary ---")
    print(f"Input rows (ISLa generated): {10 * args.n}")
    print(f"Total errors (starting with '[ERROR]'): {total_errors}")
    write_summary(args.version, args, output_row_count, total_errors, error_counter, non_critical_counter, actual_errors)
    
    if args.generate == "yes":
        creation_time_instances = end_time_instances - start_time_instances
        creation_time_templates = end_time_templates - start_time_templates
        print(f"Time instances: {creation_time_instances:.2f} seconds")
        print(f"Time templates: {creation_time_templates:.2f} seconds")

if __name__ == "__main__":
    main()
import logging
import random
import re
import subprocess
from typing import List
import rdflib
from pyvis.network import Network
import argparse
from collections import Counter
import time
from pyshacl import validate
from isla.solver import ISLaSolver
import string
import os
from isla.derivation_tree import DerivationTree
import random

logging.basicConfig(
    filename='./logs/main_lutra.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_default_version():
    version = 1
    while os.path.exists(f'./data/instances/instances{version}.stottr'):
        version += 1
    return str(version)

global args
parser = argparse.ArgumentParser(description="Generate testing instances")
parser.add_argument('-n', type=int, default=10, help='Number of instances to generate wil be multiplied by 10')
parser.add_argument('-generate', type=str, default="yes", help='Generate instances? (yes/no)')
parser.add_argument('-version', type=str, default=get_default_version(), help='Version of the output file')
args = parser.parse_args()


GRAMMAR = {
    "<start>": ["<rdf_instance>"],
    "<rdf_instance>": [
        "<footballer_instance>",
        "<club_instance>",
        "<league_instance>",
        "<country_instance>",
        "<wrong_instance>",

    ],
    "<footballer_instance>": [
        "foot:Footballer(<validID>,<valid_first_name>,<valid_last_name>,\"<validBirthday>\"^^xsd:date,<valid_current_club>,<team_list>,<valid_marketValue>,<valid_position>,<valid_country>) .",
    ],
    "<club_instance>": [
        "foot:Club(<validID>,<valid_clubIRI>,<valid_year>^^xsd:gYear,<valid_stadium>,<valid_country>) .",
    ],
    "<league_instance>": [
        "foot:League(<validID>,<valid_leagueName>,<valid_year>^^xsd:gYear,<team_list_IRI>,<team_list_IRI>) .",
    ],
    "<country_instance>": [
        "foot:Country(<validID>,<valid_country>,<valid_continent>,<valid_fifaCode>,<array_of_topPlayers>,<array_of_leagues>) .",
    ],

    "<wrong_instance>": [
        "foot:Footballer(<validID>,<random_type>,<valid_last_name>,\"<validBirthday>\"^^xsd:date,<valid_current_club>,<team_list>,<random_type>,<valid_position>,<valid_country>) .",
        "foot:Club(<validID>,<valid_clubIRI>,<random_type>,<valid_stadium>,<valid_country>) .",
        "foot:League(<validID>,<valid_leagueName>,<random_type>,<team_list_IRI>,<team_list_IRI>) .",
        "foot:Country(<validID>,<valid_country>,<random_type>,<valid_fifaCode>,<array_of_topPlayers>,<array_of_leagues>) .",
        "foot:Footballer(<validID>,<valid_first_name>,<random_type>,\"<validBirthday>\"^^xsd:date,<valid_current_club>,<team_list>,<valid_marketValue>,<random_type>,<valid_country>) .",
        "foot:Club(<validID>,<valid_clubIRI>,<valid_year>^^xsd:gYear,<random_type>,<valid_country>) .",
        "foot:League(<validID>,<valid_leagueName>,<valid_year>^^xsd:gYear,<random_type>,<team_list_IRI>) .",
        "foot:Country(<validID>,<valid_country>,<valid_continent>,<random_type>,<array_of_topPlayers>,<array_of_leagues>) .",
        "foot:Footballer(<validID>,<valid_first_name>,<valid_last_name>,\"<random_type>\"^^xsd:date,<valid_current_club>,<team_list>,<valid_marketValue>,<valid_position>,<random_type>) .",
        "foot:Club(<validID>,<random_type>,<valid_year>^^xsd:gYear,<valid_stadium>,<valid_country>) .",
    ],
    "<random_type>": [
        "<random_string>",
        "<random_string>@<language_tag>",
        "<random_number>",
        "<boolean>",
        "<validID>",
        "<validBirthday>",
        "<team_list>",
        "<valid_clubIRI>",
        "<double>"
    ],

    "<double>": [
        "<random_number>.<digit><digit>",
    ],

    "<random_number>": [
        "<digit><digit><digit><digit><digit><digit><digit><digit>",
        "<digit><digit><digit><digit><digit><digit><random_number>",
    ],
    "<boolean>": [
        "true",
        "false",
    ],

    "<validID>": ["_:<letter><letter><letter>"],
    "<valid_first_name>": ["\"Lionel\"", "\"Cristiano\"", "\"Amadou\""],
    "<valid_last_name>": [ "\"<random_string>\""
        "\"Messi\"", "\"Ronaldo\"", "\"Fernandes\"", "\"Mbappe\"", "\"O'Neil\"",
        "\"Van der Waals\"", "\"Al-Hassan\"", "\"Müller\"", "\"D'Artagnan\"", "\"Pérez\"",
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

    
    "<valid_year>": ["\"2015\"", "\"2016\"", "\"2017\"", "\"2018\"", "\"2019\""],

    
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

    
    "<valid_stadium>": [
        "\"Camp Nou\"", "\"Allianz Stadium\"", "\"Parc des Princes\"", "\"Anfield\"", "\"Old Trafford\""
    ],

    
    "<valid_leagueName>": [
        "\"La Liga\"", "\"Serie A\"", "\"Ligue 1\"", "\"Premier League\"", "\"Bundesliga\""
    ],

    
    "<valid_continent>": [
        "\"Europe\"", "\"South America\"", "\"Africa\"", "\"Asia\"", "\"North America\""
    ],

    
    "<valid_fifaCode>": ["\"ARG\"", "\"POR\"", "\"FRA\"", "\"EGY\"", "\"ENG\""],
    "<team_list_IRI>": [
    "(" + ", ".join(["<valid_team_IRI>" for _ in range(2)]) + ")",  
    "(" + ", ".join(["<valid_team_IRI>" for _ in range(4)]) + ")",  
    "(<valid_team_IRI>, <team_list_IRI>)",  
    "(<team_list_IRI>, <team_list_IRI>)", 
    "(((<team_list_IRI>, <valid_team_IRI>)<team_list_IRI>)<team_list_IRI>)",  
    "(<team_list_IRI>, <team_list_IRI>)",  
],
"<team_list_IRI>": [
    "(" + ", ".join(["<valid_team_IRI>" for _ in range(8)]) + ")",  
    "(" + ", ".join(["<valid_team_IRI>" for _ in range(16)]) + ")",  
    "(" + ", ".join(["<team_list_IRI>" for _ in range(4)] + ["<valid_team_IRI>" for _ in range(4)]) + ")",  
    "(" + ", ".join(["(<valid_team_IRI>, (<team_list_IRI>, (<valid_team_IRI>)))" for _ in range(8)]) + ")",  
    "(<team_list_IRI>, <team_list_IRI>)"  
],
    "<valid_team_IRI>": ["<valid_clubIRI>"],
    
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

    
    "<array_of_topPlayers>": [
        "( )",
        "(<valid_player>)",
        "(<valid_player>, <valid_player>)",
        "(<valid_player>, <valid_player>, <valid_player>)"
    ],
    "<valid_player>": ["<valid_first_name> <valid_last_name>"],  

    
    "<array_of_leagues>": [
        "( )",
        "(<valid_league>)",
        "(<valid_league>, <valid_league>)",
        "(<valid_league>, <valid_league>, <valid_league>)"
    ],
    "<valid_league>": ["<validID>"],
    "<random_string>": [
        "\"<letter><letter><letter><letter>\"",
        "\"<letter><letter><letter><letter><letter><random_string>\"",
    ],

    
    "<letter>": list(string.ascii_letters),
    "<digit>": list(string.digits),
    "<OneToNine>": list(string.digits[1:]),
    "<language_tag>": [
        "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko",
        "ar", "nl", "sv", "da", "fi", "no", "pl", "tr", "cs", "hu",
        "ro", "sk", "bg", "el"
    ]
}

def validate_with_shacl(graph_file, shapes_file='football_shacl.ttl'):
    data_graph = rdflib.Graph().parse(graph_file, format='turtle')
    shapes_graph = rdflib.Graph().parse(shapes_file, format='turtle')
        
    conforms, results_graph, results_text = validate(data_graph, shacl_graph=shapes_graph)
    if not conforms:
        print("SHACL validation failed:\n")
    else:
        print("SHACL validation passed!")
    
    return conforms, results_graph, results_text

def measure_coverage(derivation_trees: List[DerivationTree], grammar: dict, grammar_name: str = "Grammar") -> float:
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
    print(f"{grammar_name} Rule Coverage: {len(used_rules)}/{len(all_rules)} rules used ({coverage:.2%})")
    unused_rules = all_rules - used_rules
    if unused_rules:
        print(f"{grammar_name} Unused rules: {unused_rules}")
    else:
        print(f"{grammar_name}: All rules were used.")
    return coverage

def get_non_terminals(tree: DerivationTree) -> set:
    non_terminals = set()
    if tree.children:
        non_terminals.add(tree.value.strip("<>"))
        for child in tree.children:
            non_terminals.update(get_non_terminals(child))
    return non_terminals

def write_prefixes(version, generate_flag):
    prefixes = [
        "@prefix ottr: <http://ns.ottr.xyz/0.4/> .\n",
        "@prefix o-rdf: <http://tpl.ottr.xyz/rdf/0.1/> .\n",
        "@prefix foot: <http://example.org/football#> .\n",
        "@prefix schema: <http://schema.org/> .\n",
        "@prefix foaf: <http://xmlns.com/foaf/0.1/> .\n",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n",
    ]
    if generate_flag == "yes":
        with open(f'./data/instances/instances{version}.stottr', 'w', encoding='utf-8') as file:
            file.writelines(prefixes)

def count_unique_derivation_trees(derivation_trees: List[DerivationTree]) -> int:
    unique_trees = set(str(tree) for tree in derivation_trees)
    print(f"Unique derivation trees: {len(unique_trees)}")
    return len(unique_trees)

def generate_instances(n, version):
    start_time = time.time()
    generated_inputs = []
    derivation_trees = []
    valid_instance_count = 0
    for _ in range(n):
        solver = ISLaSolver(grammar=GRAMMAR)
        with open(f'./data/instances/instances{version}.stottr', 'a', encoding='utf-8') as instances_file:
            for _ in range(10):
                tree = solver.solve()
                instance = str(tree)
                instances_file.write(f"{instance}\n")
                generated_inputs.append(instance)
                derivation_trees.append(tree)
                if solver.check(tree):
                    valid_instance_count += 1
    count_unique_derivation_trees(derivation_trees)
    print(f"Valid instances generated: {valid_instance_count}/{n * 10}")
    end_time = time.time()
    print(f"Time taken to create instances: {end_time - start_time:.2f} seconds")
    return start_time, end_time, generated_inputs, derivation_trees

def run_lutra(version):
    try:
        lutra_cmd = [
            'java', '-Xms2G', '-jar', 'lutra.jar', '--mode', 'expand',
            '-L', 'stottr', '-l', 'football.stottr', '-f',
            '-I', 'stottr', f'./data/instances/instances{version}.stottr', '-o',
            f'./data/output/output{version}.ttl'
        ]
        result = subprocess.run(lutra_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logging.info(f"Processing batch: instances{version}.stottr")
        logging.info(f"Lutra errors: {result.stderr}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running Lutra: {e}")
        print("Exiting program.")
        exit(1)


def process_lutra_errors(result):
    output_row_count = result.stdout.count('\n')
    error_lines = [line for line in result.stderr.split('\n') if line.strip()]
    actual_errors = [line for line in error_lines if "[ERROR]" in line]
    non_critical_messages = [line for line in error_lines if "[ERROR]" not in line]

    error_counter = Counter(actual_errors)
    non_critical_counter = Counter(non_critical_messages)
    total_errors = sum(error_counter.values())
    fatal_errors = [line for line in actual_errors if "[FATAL]" in line]

    if fatal_errors:
        print(f"Fatal error occurred: {fatal_errors}")
        print("Exiting program.")
        exit(1)

    return output_row_count, error_counter, non_critical_counter, total_errors, actual_errors


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

        stats_file.write("Aggregated error counts (by exact message, actual errors):\n")
        for error, count in error_counter.most_common():
            stats_file.write(f"'{error}': {count}\n")
        
        if non_critical_counter:
            stats_file.write("\nNon-critical messages (not starting with '[ERROR]'):\n")
            for msg, count in non_critical_counter.most_common():
                stats_file.write(f"'{msg}': {count}\n")

def validate_rdf_turtle(version):
    graph = rdflib.Graph()
    try:
        graph.parse(f'./data/output/output{version}.ttl', format='turtle')
        print("\nThe output file is valid RDF/Turtle syntax.")
    except Exception as e:
        print(f"Error parsing the TTL file: {e}")
        exit(1)    
    return graph

def main():

    get_default_version()

    write_prefixes(args.version, args.generate)
    
    if args.generate == "yes":
        start_time, end_time, generated_instances,derivation_trees = generate_instances(args.n, args.version)
        print("Creating, be patient... (The next Messi is being born!)")
        coverage = measure_coverage(derivation_trees, GRAMMAR, "Football Instances")
        print(f"Grammar coverage: {coverage:.2%}")
    else:
        start_time = end_time = 0

    result = run_lutra(args.version)
    output_row_count, error_counter, non_critical_counter, total_errors, actual_errors = process_lutra_errors(result)
  

    print("\n--- Summary ---")
    print(f"Input rows (ISLa generated): {10 * args.n}")
    print(f"Output rows (Turtle file): {output_row_count}")
    print(f"Total errors (starting with '[ERROR]'): {total_errors}")

    write_summary(args.version, args, output_row_count, total_errors, error_counter, non_critical_counter, actual_errors)
    
    print("\nValidating with SHACL...")
    shacl = validate_with_shacl(f'./data/output/output{args.version}.ttl')
    logging.info(shacl[2])
    if not shacl[0]:
        print(f"SHACL validation failed")
        
    else:
        print("SHACL validation passed")

    validate_rdf_turtle(args.version)
    
    if args.generate == "yes":
        creation_time = end_time - start_time
        print(f"Time taken to create instances: {creation_time:.2f} seconds")

if __name__ == "__main__":
    main()

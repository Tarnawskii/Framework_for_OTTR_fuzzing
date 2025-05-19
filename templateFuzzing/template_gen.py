import logging
import subprocess
import argparse
import time
from isla.solver import ISLaSolver
from isla.language import DerivationTree
import string
import os
import re
from typing import List
from collections import Counter

def get_default_version():
    version = 1
    while os.path.exists(f'./data/templates/templates{version}.stottr'):
        version += 1
    return str(version)


parser = argparse.ArgumentParser(description="Fuzz and test stOTTR-templates.")
parser.add_argument('-n', type=int, default=10, help='Amount of templates to generate will be multiplied by 10')
parser.add_argument('-version', type=str, default=get_default_version(), help='Versiono')
parser.add_argument('-generate', action='store_true', help='Generet templates')

args = parser.parse_args()

logging.basicConfig(
    filename=f'./logs/template_log_{args.version}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
TEMPLATE_GRAMMAR = {
    "<start>": ["<template>"],
    "<template>": [
        "<signature> :: { <pattern_list> } .",               
        "<signature> :: BASE .",                            
        "<correct_signature> :: { <correct_pattern_list> } .", 
        "<malformed_templates>",
    ],
    "<malformed_templates>": [
        "<signature> :: { <pattern_list> ",                  
        "<signature> :: BASE",                                
        "<template_name> [ <parameter_list> ] { <pattern_list> } .",  
        "<signature> <between> { <pattern_list> } <extra_dot>",       
        "<signature> :: { <pattern_list> }",                  
        "<signature> :: ( <pattern_list> ) .",                                         
        "<signature> :: { <pattern_list> } <invalid_punctuation>" ],
    "<between>": ["::", "<special_char>:", ":", ";"],         
    "<extra_dot>": ["", ".", "..", "..."],                    
    "<invalid_punctuation>": [",", ";", "(", ")"],            
    "<signature>": [
        "<template_name> [ <parameter_list> ] <annotation_list>", 
        "<template_name> [ <parameter_list> ]",                    
        "<correct_template_name> [ <correct_parameter_list> ]",   
        "<template_name> <parameter_list> <annotation_list>",      
        "<template_name> [ <parameter_list> <annotation_list>",    
        "<template_name> [ ]",                                    
        "<template_name>",                                        
    ],
    "<invalid_term>": ["<string>", "<malformed_iri>", "<malformed_literal>", "<invalid_name>"],
    "<template_name>": ["<prefixed_name>", "<malformed_iri>", "<ottr:IRI>", "<invalid_name>"],
    "<prefixed_name>": ["<prefix>:<local_name>"],
    "<prefix>": ["foot", "ex", "ottr", "o-rdf", "xsd", "owl", "http://example.com/", "badPrefix", ""], 
    "<local_name>": ["Footballer", "Template1", "Template2", "Triple", "Type", "Annotation", "Invalid Space"],
    "<malformed_iri>": [
        "ex:Invalid Space", "ex:", ":noPrefix", "<unclosedIRI", "ex::doubleColon",
        "http://invalid", "://noScheme", "bad::IRI", ""        
    ],
    "<argument_list>": [
        "<argument>", "<argument> , <argument_list>",],
    "<invalid_list_expander>": [
        "invalid | ", "badPrefix:| ", "badPrefix:| badPrefix:|"],
    "<invalid_name>": ["var", "123", "\"string\""],          
    "<correct_template_name>": ["foot:Footballer"],
    "<parameter_list>": [
        "<parameter>",
        "<parameter> , <parameter_list>",
        "<correct_parameter_list>",
        "",                          
        "<parameter> <parameter_list>", 
        "<parameter> , , <parameter_list>", 
        "<parameter> ,",                     
        "<invalid_term>"                   
    ],
    "<correct_parameter_list>": [
        "ottr:IRI ?personIRI, xsd:string ?firstName, xsd:string ?lastName, xsd:date ?birthday, xsd:string ?currentClub, List<<xsd:string>> ?clubHistory, xsd:integer ?marketValue, xsd:string ?countryName"
    ],
    "<parameter>": [
        "<modifiers> <type> <variable> <default_value>",  
        "<modifiers> <variable> <default_value>",       
        "<type> <variable>",                            
        "<modifiers> <type> <variable> = <malformed_constant>",  
        "<modifiers> <malformed_literal> <variable>",       
        "<modifiers> <type>",                           
        "<parameter_name> ?<variable_name>",
        "<list_parameter> ?<variable_name>",
        "<type> <invalid_term>",                       
        "<list_expander> <type> <variable>"             
    ],
    "<modifiers>": ["", "?", "!", "?!", "?!!", "??", " ", "++", "++ ++"],
    "<type>": [
        "<literal>",
        "<list_type>"
        "<malformed_literal>",
    ],
    "<list_type>": [
        "List<<type>>",
        "NEList<<type>>",
        "LUB<<type>>",
        "List<<<type>>>",
        "LUB<<List<<type>>>>",
        "NEList<<LUB<<type>>>>",
    ],
      "<literal>": [
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
    "<malformed_literal>": [
        "xsd:invalidType", "ottr:", "badPrefix:string", "List", "LUB",
        ":noType", "invalid", "xsd::doubleColon", ""     
    ],
    "<parameter_name>": ["<parameter_type>:<datatype>", "<invalid_name>"],
    "<parameter_type>": ["ottr", "foot", "xsd", "none", "bad"],
    "<datatype>": ["<prefixed_name>", "<literal_type>", "foaf:name", "foot:clubHistory", "<malformed_iri>"],
    "<literal_type>": ["string", "integer", "decimal", "boolean", "date", "invalid"],
    "<list_parameter>": [
        "List<<parameter>>", "List<List<<list_parameter>>>", "<NEList>", "<LUBList>", "<term_list>",
        "List<<invalid_term>>",                         
        "<list_expander> List<<type>>",
        "List<<literal>>"               
    ],
    "<NEList>": ["NEList<<parameter>>", "NEList<List<<list_parameter>>>", "NEList<<invalid_term>>"],
    "<LUBList>": ["LUB<<type>>", "LUB<List<<type>>>", "LUB<<malformed_literal>>"],
    "<variable>": ["?<variable_name>", "<invalid_variable>"],
    "<variable_name>": ["<char>", "<char><variable_name>"],
    "<char>": list(string.ascii_letters) + list(string.digits) + list(string.punctuation),
    "<invalid_variable>": ["", "123", "\"string\""],  
    "<default_value>": ["", "= <constant_term>", "= <variable>", "= <malformed_constant>"],
    "<constant_term>": ["<constant>", "( <constant_term_list> )", "( <constant_term_list> ", "<invalid_term>"],
    "<constant_term_list>": ["<constant_term>", "<constant_term> , <constant_term_list>", "", "<constant_term> ,,"],
    "<constant>": [
        "<prefixed_name>", "\"<string>\"", "<integer>", "<decimal>", "<boolean>",
        "\"2023-01-01\"^^xsd:date", "none", "_:b1", "_:b2",
        "\"malformed\"^^bad:datatype", "\"unclosed", "23.14.15",
        "\"invalid\"^^<malformed_iri>"                   
    ],
    "<string>": ["\"<char>\"", "\"<char>*\"", "\"<char>+\"", "\"<char>*<char><char>*\"", "\"unclosed"],
    "<integer>": ["<digit>+", "-<digit>+", "abc"],   
    "<decimal>": ["<integer>.<integer>", "1..2"],     
    "<boolean>": ["true", "false", "invalid"],         
    "<digit>": list(string.digits),
    "<malformed_constant>": [
        "\"unclosed", "23.14.15", "\"malformed\"^^bad:datatype",
        "\"value\"^^invalid", "invalid^^type"     
    ],
    "<annotation_list>": [
        "", "<instance>", "<instance> , <instance>",
        "<instance> <instance>", "<instance>", "<malformed_instance>",
        "<invalid_term>",                              
        "<instance> <invalid_punctuation>",            
        "<list_expander> <instance>"                  
    ],
    "<pattern_list>": [
        "<pattern>", "<pattern> , <pattern_list>", "<correct_pattern_list>",
        "", "<pattern> <pattern_list>", "<pattern> ,",
        "<invalid_term>",                                
        "<pattern> <invalid_punctuation>",               
        "<instance>"                                      
    ],
    "<correct_pattern_list>": [
        "o-rdf:Type(?personIRI, foot:Footballer), ottr:Triple(?personIRI, foaf:name, ?firstName), "
        "ottr:Triple(?personIRI, foaf:lastName, ?lastName), ottr:Triple(?personIRI, foot:birthday, ?birthday), "
        "ottr:Triple(?personIRI, foot:currentClub, ?currentClub), ottr:Triple(?personIRI, foot:clubHistory, ?clubHistory), "
        "ottr:Triple(?personIRI, foot:marketValue, ?marketValue), ottr:Triple(?personIRI, foot:countryName, ?countryName)"
    ],
    "<pattern>": [
        "ottr:Triple(<subject>, <predicate>, <object>)",
        "o-rdf:Type(<subject>, <object>)",
        "ottr:Triple(<subject> <predicate> <object>)",   
        "<malformed_iri>(<subject>, <object>)"            
    ],
    "<subject>": ["?<variable_name>", "<invalid_term>", "_:blank"],  
    "<predicate>": ["<prefixed_name>", "<malformed_iri>"],
    "<object>": ["?<variable_name>", "<constant>", "<invalid_term>"],
    "<instance>": [
        "<list_expander> <template_name> ( <argument_list> )",
        "<template_name> ( <argument_list> )",
        "<template_name> <argument_list>"                
    ],
    "<malformed_instance>": [
        "ex:Template1 ( ?<variable_name>",               
        "<template_name> ?<variable_name> )",
        "<template_name> ( <invalid_term> )",           
        "<invalid_list_expander> <template_name> ( <argument_list> )"  
    ],
    "<list_expander>": ["cross | ", "zipMin | ", "zipMax |" ],                 

    "<argument>": [
        "++ <term>", "<term>", "++ <term>",
        "<term> ^^ <malformed_literal>",                  
        "_:blank"                                       
    ],
    "<term>": ["<variable>", "<constant>", "( <term_list> )", "( <term_list> ) )", "<malformed_term>"],
    "<malformed_term>": ["?var 1", "\"string\"^^^xsd:string", "( , )", "invalid term"],
    "<term_list>": ["<term>", "<term> , <term_list>", "", "<term> ,,"],
    "<special_char>": list(string.punctuation),
    "<ottr:IRI>": ["ottr:IRI"],
    "<correct_signature>": [
        "foot:Footballer [ ottr:IRI ?personIRI, xsd:string ?firstName, xsd:string ?lastName, "
        "xsd:date ?birthday, xsd:string ?currentClub, List<<xsd:string>> ?clubHistory, "
        "xsd:decimal ?marketValue, xsd:string ?countryName ]"
    ],
    "<xsd:string>": ["xsd:string"],
}

def measure_coverage(derivation_trees: List[DerivationTree], grammar: dict, grammar_name: str = "Template Grammar") -> float:
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

def count_unique_derivation_trees(derivation_trees: List[DerivationTree]) -> int:
    unique_trees = set(str(tree) for tree in derivation_trees)
    print(f"Unique derivation trees: {len(unique_trees)}")
    return len(unique_trees)

def write_prefixes(version):
    prefixes = [
        "@prefix ottr: <http://ns.ottr.xyz/0.4/> .\n",
        "@prefix o-rdf: <http://tpl.ottr.xyz/rdf/0.1/> .\n",
        "@prefix foot: <http://example.org/football#> .\n",
        "@prefix schema: <http://schema.org/> .\n",
        "@prefix foaf: <http://xmlns.com/foaf/0.1/> .\n",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
    ]
    with open(f'./data/templates/templates{version}.stottr', 'w', encoding='utf-8') as file:
        file.writelines(prefixes)

def generate_templates(n, version):
    start_time = time.time()
    generated_templates = []
    derivation_trees = []
    for _ in range(n):
        solver = ISLaSolver(grammar=TEMPLATE_GRAMMAR)
        with open(f'./data/templates/templates{version}.stottr', 'a', encoding='utf-8') as templates_file:
            for _ in range(10):
                tree = solver.solve()  
                template = str(tree)  
                templates_file.write(f"{template}\n")
                generated_templates.append(template)
                derivation_trees.append(tree)
    end_time = time.time()
    print(f"Time generating templates: {end_time - start_time:.2f}")
    return start_time, end_time, generated_templates, derivation_trees

def run_lutra(version):
    try:
        with open('./data/instances/dummy_instance.stottr', 'w', encoding='utf-8') as dummy_file:
            dummy_file.write("""@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix foot: <http://example.org/football#> .
@prefix ottr: <http://ns.ottr.xyz/0.4/> .
@prefix o-rdf: <http://tpl.ottr.xyz/rdf/0.1/> .
@prefix schema: <http://schema.org/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
foot:Footballer(_:player1, "Lionel", "Messi", "1987-06-24"^^xsd:date, "Paris Saint-Germain", ("Barcelona", "Paris Saint-Germain"), "80000000.00"^^xsd:decimal, "Argentina").""")
        
        lutra_cmd = [
            'java', '-Xms2G', '-jar', 'lutra.jar', '--mode', 'expand',
            '-L', 'stottr', '-l', f'./data/templates/templates{version}.stottr', '-f',
            '-I', 'stottr', './data/instances/dummy_instance.stottr'
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
        with open(f'./data/output/rawOutput/output{version}.ttl', 'w', encoding='utf-8') as output_file:
            output_file.write(result.stdout)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error occured running lutra: {e}")
        exit(1)

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
        exit(1)
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

def write_summary(version, output_row_count, total_errors, error_counter, non_critical_counter, actual_errors, template_coverage):
    aggregated_error_types = aggregate_error_types(error_counter)
    with open(f'./data/stats/stats{version}.txt', 'w', encoding='utf-8') as stats_file:
        stats_file.write("--- Oppsummering ---\n")
        stats_file.write(f"Genererte templates: {10 * args.n}\n")
        stats_file.write(f"Output rows (Turtle file): {output_row_count}\n")
        stats_file.write(f"Template Rule Coverage: {template_coverage:.2%}\n")
        try:
            stats_file.write(f"Last error: {actual_errors[-1]}\n\n")
        except IndexError:
            stats_file.write("No actual errors found.\n\n")
        stats_file.write("Aggregated error counts (by type):\n")
        for error_type, count in aggregated_error_types.most_common():
            stats_file.write(f"{error_type}: {count}\n")
        stats_file.write("\nExact error messages:\n")
        for error, count in error_counter.most_common():
            stats_file.write(f"'{error}': {count}\n")
        if non_critical_counter:
            stats_file.write("\nNon-critical messages:\n")
            for msg, count in non_critical_counter.most_common():
                stats_file.write(f"'{msg}': {count}\n")

def main():
    template_coverage = 0
    if args.generate:
        print("Genererer templates...")
        write_prefixes(args.version)
        start_time, end_time, _, derivation_trees = generate_templates(args.n, args.version)
        print("Templates generert.")
        
        template_coverage = measure_coverage(derivation_trees, TEMPLATE_GRAMMAR)
        count_unique_derivation_trees(derivation_trees)

    result = run_lutra(args.version)
    output_row_count, error_counter, non_critical_counter, actual_errors = process_lutra_errors(result)
    total_errors = sum(error_counter.values())

    write_summary(args.version, output_row_count, total_errors, error_counter, non_critical_counter, actual_errors, template_coverage)

    print("\n--- Oppsummering ---")
    print(f"Genererte templates: {10 * args.n}")
    print(f"Output rows (Turtle file): {output_row_count}")
    print(f"Totalt antall feil: {total_errors}")
    print(f"Template Rule Coverage: {template_coverage:.2%}")

main()
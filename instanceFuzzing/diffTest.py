import logging
import subprocess
import rdflib
from rdflib.collection import Collection
import os
from rdflib.compare import to_isomorphic, graph_diff
import tempfile
import time
import argparse
from ottr import OttrGenerator

PYOTTR_ERROR_LOG_FILE = "./differential/pyottr_errors.log"
LUTRA_ERROR_LOG_FILE = "./differential/lutra_errors.log"
TEST_RESULTS_LOG = "./differential/test_results.log"
AGGREGATED_ERRORS_LOG = "./differential/aggregated_errors.log"

global args
parser = argparse.ArgumentParser(description="Metamorphic diff test of pyOTTR and Lutra.")
parser.add_argument("input_file", help="Input instance file.")
parser.add_argument("--save-instances", help="Should isolated instance files be saved", default=None)
args = parser.parse_args()

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
pyottr_logger = logging.getLogger("pyOTTR")
pyottr_logger.addHandler(logging.FileHandler(PYOTTR_ERROR_LOG_FILE))
lutra_logger = logging.getLogger("Lutra")
lutra_logger.addHandler(logging.FileHandler(LUTRA_ERROR_LOG_FILE))

def log_error(logger, message, category):
    logger.error(f"[{category}] {message}")

def process_instance_pyottr(template, instance_str):
    try:
        generator = OttrGenerator()
        generator.load_templates(template)
        instance_handler = generator.instanciate(instance_str, "stottr")
        triples = list(instance_handler.execute())
        graph = rdflib.Graph()
        for triple in triples:
            s, p, o = triple
            if isinstance(o, list):
                list_head = rdflib.BNode()
                Collection(graph, list_head, o)
                o = list_head
            graph.add((s, p, o))
        return graph, None
    except Exception as e:
        log_error(pyottr_logger, f"Error in pyOTTR: {e}")
        return None, str(e)

def process_instance_lutra(template, instance_str):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.stottr') as template_file:
        template_file.write(template.encode('utf-8'))
        template_file_path = template_file.name
    with tempfile.NamedTemporaryFile(delete=False, suffix='.stottr') as instance_file:
        instance_file.write(instance_str.encode('utf-8'))
        instance_file_path = instance_file.name
    with tempfile.NamedTemporaryFile(delete=False, suffix='.ttl') as output_file:
        output_file_path = output_file.name

    cmd = [
        'java', '-jar', 'lutra.jar', '--mode', 'expand', '-L', 'stottr',
        '-l', template_file_path, '-f', '-I', 'stottr', instance_file_path, '-o', output_file_path
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if result.returncode != 0:
            log_error(lutra_logger, f"Error in Lutra: {result.stderr}")
            return None, result.stderr
        graph = rdflib.Graph()
        graph.parse(output_file_path, format='turtle')
        return graph, None
    except Exception as e:
        log_error(lutra_logger, f"Error parsing Lutra output: {e}")
        return None, str(e)

def compare_outputs(pyottr_result, lutra_result, pyottr_error, lutra_error, instance, instance_num):
    log_msg = f"Instanc {instance_num}: {instance.strip()}\n"
    if pyottr_result and lutra_result:
        iso_pyottr = to_isomorphic(pyottr_result)
        iso_lutra = to_isomorphic(lutra_result)
        if iso_pyottr == iso_lutra:
            log_msg += "OK (Graphs are isomorphic)\n"
        else:
            log_msg += "Graphs are not isomorphic\n"
            in_both, in_first, in_second = graph_diff(iso_pyottr, iso_lutra)
            log_msg += f"Difference:\nOnly i pyOTTR: {in_first}\nOnly in Lutra: {in_second}\n"
        
        output_pyottr = f"./differential/data/output/{args.input_file}pyottr_instance_{instance_num}.ttl"
        output_lutra = f"./differential/data/output/{args.input_file}lutra_instance_{instance_num}.ttl"
        if not os.path.exists(os.path.dirname(output_pyottr)):
            os.makedirs(os.path.dirname(output_pyottr))
        if not os.path.exists(os.path.dirname(output_lutra)):
            os.makedirs(os.path.dirname(output_lutra))
        pyottr_result.serialize(output_pyottr, format='turtle')
        lutra_result.serialize(output_lutra, format='turtle')
        log_msg += f"Output saved sa: {output_pyottr}, {output_lutra}\n"
    elif pyottr_error and lutra_error:
        if pyottr_error == lutra_error:
            log_msg += f"Result: Both failed with the same error: {pyottr_error}\n"
        else:
            log_msg += f"Result: Both failed, but with different errors:\npyOTTR error: {pyottr_error}\nLutra error: {lutra_error}\n"
        if pyottr_result:
            log_msg += f"Result: pyOTTR succeeded, Lutra failed\nLutra error: {lutra_error}\n"
        else:
            log_msg += f"Result: Lutra succeeded, pyOTTR failed\npyOTTR error: {pyottr_error}\n"
        return log_msg
    return log_msg

def main(input_file):
    template = """
    @prefix ottr: <http://ns.ottr.xyz/0.4/> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix foaf: <http://xmlns.com/foaf/0.1/> .
    @prefix schema: <http://schema.org/> .
    @prefix foot: <http://example.org/football#> .
    @prefix o-rdf: <http://tpl.ottr.xyz/rdf/0.1/> .

    foot:Footballer[
      ottr:IRI ?personIRI,
      xsd:string ?firstName,
      xsd:string ?lastName, 
      xsd:date ?dateOfBirth, 
      ? ottr:IRI ?currentClub, 
      ? List<ottr:IRI> ?clubHistory, 
      xsd:integer ?marketValue, 
      xsd:string ?position, 
      xsd:string ?country
    ] :: {
      o-rdf:Type(?personIRI, foot:Footballer),
      ottr:Triple(?personIRI, foaf:name, ?firstName),
      ottr:Triple(?personIRI, foaf:familyName, ?lastName),
      ottr:Triple(?personIRI, foaf:birthDate, ?dateOfBirth),
      ottr:Triple(?personIRI, foot:currentClub, ?currentClub),
      ottr:Triple(?personIRI, foot:clubHistory, ?clubHistory),
      ottr:Triple(?personIRI, foot:marketValue, ?marketValue),
      ottr:Triple(?personIRI, foot:position, ?position),
      ottr:Triple(?personIRI, foot:country, ?country)
    }.

    foot:Club[ 
      ottr:IRI ?clubIRI,
      xsd:string ?clubName,
      xsd:gYear ?foundedYear,
      xsd:string ?stadiumName,
      ottr:IRI ?country
    ] :: {
      o-rdf:Type(?clubIRI, foot:Club),
      ottr:Triple(?clubIRI, foaf:name, ?clubName),
      ottr:Triple(?clubIRI, foot:foundedYear, ?foundedYear),
      ottr:Triple(?clubIRI, foot:stadiumName, ?stadiumName),
      ottr:Triple(?clubIRI, foot:country, ?country)
    }.

    foot:League[ 
      ottr:IRI ?leagueIRI,
      xsd:string ?leagueName,
      xsd:gYear ?foundedYear, 
      List<ottr:IRI> ?topTeams,
      List<ottr:IRI> ?teams
    ] :: {
      o-rdf:Type(?leagueIRI, foot:League),
      ottr:Triple(?leagueIRI, foaf:name, ?leagueName),
      ottr:Triple(?leagueIRI, foot:foundedYear, ?foundedYear),
      ottr:Triple(?leagueIRI, foot:topTeams, ?topTeams),
      ottr:Triple(?leagueIRI, foot:teams, ?teams)
    }.

    foot:Country[ 
      ottr:IRI ?countryIRI,
      xsd:string ?countryName,
      xsd:string ?continent,
      xsd:string ?fifaCode, 
      List<ottr:IRI> ?famousPlayers,
      List<ottr:IRI> ?leagues
    ] :: {
      o-rdf:Type(?countryIRI, foot:Country),
      ottr:Triple(?countryIRI, foaf:name, ?countryName),
      ottr:Triple(?countryIRI, foot:continent, ?continent),
      ottr:Triple(?countryIRI, foot:fifaCode, ?fifaCode),
      ottr:Triple(?countryIRI, foot:famousPlayers, ?famousPlayers),
      ottr:Triple(?countryIRI, foot:leagues, ?leagues)
    }.
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        instances = [line.strip() for line in f if line.strip()]

    if args.save_instances:
        output_dir = args.save_instances
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        for i, instance in enumerate(instances, start=1):
            file_path = os.path.join(output_dir, f"./differential/instance_{i}.stottr")
            with open(file_path, "w", encoding="utf-8") as f_out:
                f_out.write(instance + "\n")
        return
    both_valid_count = 0      
    pyottr_ok_count = 0        
    lutra_ok_count = 0          
    both_failed_same_count = 0  
    both_failed_diff_count = 0  
    one_success_one_fail_count = 0 
    non_isomorphic_count = 0   

    pyottr_error_dict = {}
    lutra_error_dict = {}

    for log_file in [PYOTTR_ERROR_LOG_FILE, LUTRA_ERROR_LOG_FILE, TEST_RESULTS_LOG, AGGREGATED_ERRORS_LOG]:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("")

    with open(TEST_RESULTS_LOG, "a", encoding="utf-8") as log_file:
        for i, instance in enumerate(instances, start=1):
            if instance.startswith("@prefix"):
                continue
            print(f"\nProcessing {i}: {instance}")
            start_time = time.time()
            instance = """@prefix ottr: <http://ns.ottr.xyz/0.4/> .
@prefix o-rdf: <http://tpl.ottr.xyz/rdf/0.1/> .
@prefix foot: <http://example.org/football#> .
@prefix schema: <http://schema.org/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> . \n""" + instance
            pyottr_result, pyottr_error = process_instance_pyottr(template, instance)
            lutra_result, lutra_error = process_instance_lutra(template, instance)
            end_time = time.time()
            processing_time = end_time - start_time
            if pyottr_result:
                pyottr_ok_count += 1
            if lutra_result:
                lutra_ok_count += 1

            if pyottr_result and lutra_result:
                both_valid_count += 1
                iso_pyottr = to_isomorphic(pyottr_result)
                iso_lutra = to_isomorphic(lutra_result)
                if iso_pyottr != iso_lutra:
                    non_isomorphic_count += 1

                py_output = f"./differential/pyottr_output_{i}.ttl"
                lutra_output = f"./differential/lutra_output_{i}.ttl"
                pyottr_result.serialize(py_output, format='turtle')
                lutra_result.serialize(lutra_output, format='turtle')
            elif pyottr_error and lutra_error:
                pyottr_error_dict[pyottr_error] = pyottr_error_dict.get(pyottr_error, 0) + 1
                lutra_error_dict[lutra_error] = lutra_error_dict.get(lutra_error, 0) + 1
                if pyottr_error == lutra_error:
                    both_failed_same_count += 1
                else:
                    both_failed_diff_count += 1
            else:
                one_success_one_fail_count += 1
                if pyottr_error and not lutra_error:
                    lutra_ok_count += 0
                    lutra_error_dict[lutra_error] = lutra_error_dict.get(lutra_error, 0) 
                    pyottr_error_dict[pyottr_error] = pyottr_error_dict.get(pyottr_error, 0) + 1
                elif lutra_error and not pyottr_error:
                    pyottr_ok_count += 0
                    lutra_error_dict[lutra_error] = lutra_error_dict.get(lutra_error, 0) + 1

            log_msg = compare_outputs(pyottr_result, lutra_result, pyottr_error, lutra_error, instance, i)
            log_file.write(log_msg + "\n")
    summary = "\n=== Test Summary ===\n"
    summary += f"Number of instances tested: {len(instances)}\n"
    summary += f"Both tools valid (output): {both_valid_count}\n"
    summary += f"pyOTTR OK: {pyottr_ok_count}\n"
    summary += f"Lutra OK: {lutra_ok_count}\n"
    summary += f"Both failed with the same error: {both_failed_same_count}\n"
    summary += f"Both failed with different errors: {both_failed_diff_count}\n"
    summary += f"One succeeded and one failed: {one_success_one_fail_count}\n"
    summary += f"Valid instances with non-isomorphic graphs: {non_isomorphic_count}\n\n"
    summary += "Aggregated pyOTTR errors:\n"
    for err, count in pyottr_error_dict.items():
        summary += f"  {err}: {count}\n"
    summary += "\nAggregated Lutra errors:\n"
    for err, count in lutra_error_dict.items():
        summary += f"  {err}: {count}\n"

    with open(AGGREGATED_ERRORS_LOG, "w", encoding="utf-8") as agg_log:
        agg_log.write(summary)

    print(summary)
    print(f"Detailed results logged to {TEST_RESULTS_LOG}")
    print(f"pyOTTR errors logged to {PYOTTR_ERROR_LOG_FILE}")
    print(f"Lutra errors logged to {LUTRA_ERROR_LOG_FILE}")
    print(f"Aggregated errors logged to {AGGREGATED_ERRORS_LOG}")

    if both_valid_count == 0:
        print("No valid instances found.")

main(args.input_file)
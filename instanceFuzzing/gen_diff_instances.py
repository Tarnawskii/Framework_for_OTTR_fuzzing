
import os
import argparse
import string
from isla.solver import ISLaSolver

def get_default_version():
    version = 1
    while os.path.exists(f'./differential/data/instances/instances{version}.stottr'):
        version += 1
    return str(version)
global args
parser = argparse.ArgumentParser(description="Differential instance generator")
parser.add_argument('-n', type=int, default=10, help='Number of instances')
parser.add_argument('-version', type=str, default=get_default_version(), help='Version of the output file')
args = parser.parse_args()

pyOTTR_GRAMMAR = {
    "<start>": ["<rdf_instance>"],
    "<rdf_instance>": [
        "<malformed_instance>",
        "foot:Country(<id>,<countryName>^^xsd:string,<continent>^^:xsd:string,<fifaCode>^^xsd:string,<array_of_topPlayers>^^List<<xsd:string>>,<array_of_leagues>) <dot>",
        "foot:League(<id>,<leagueName>^^xsd:string,<countryName>^^xsd:string,<array_of_teams>, <array_of_teams>) <dot>",
        "foot:Club(<id>,<clubName>^^xsd:string,<year>^^gYear, \"<stadium_name>\"^^xsd:string, <countryName>^^xsd:string) <dot>",
        "foot:Footballer(<id>,<first_name>^^xsd:string,<last_name>^^xsd:string,<birthday>^^xsd:date,<current_club>,<array_of_teams>,<marketValue>^^xsd:integer,<position>^^xsd:string,<countryName>^^xsd:string) <dot>"
    ],
    "<argument_list>": ["<argument>", "<argument>,<argument_list>"],
    "<argument>": ["<term>", "++<term>"],
    "<term>": [
        "<id>", "<first_name>", "<last_name>", "<birthday>", "<current_club>",
        "<array_of_teams>", "<marketValue>", "<position>", "<countryName>",
        "<clubName>", "<year>", "<stadium>", "<leagueName>", "<continent>",
        "<fifaCode>", "<array_of_topTeams>", "<array_of_topPlayers>",
        "<array_of_leagues>", "none", "<variable>"
    ],
    "<variable>": ["?<letter><letter><letter>"],  
    "<malformed_instance>": [
        "foot:Footballer(<id>",  
        "foot:Club(<id>,)",  
        "foot:League(<argument_list>,<extra>)",  
        "foot:Country(<argument_list>",  
        "foot:Footballer(<id>,<first_name>,<last_name>,<birthday>^^<invalid_datatype>,<current_club>,<array_of_teams>,<marketValue>,<position>,<countryName>)",  
        "foot:Footballer(<id>,<first_name>,<last_name>,<birthday>^^xsd:date,none,<array_of_teams>,<marketValue>,<position>,<countryName>)",  
        "foot:Club(<id>,<clubName>,<year>^^xsd:gYear<comma><stadium>,<countryName>)",  
    ],
    "<dot>": [".", " ", "<special_character>"],
    "<comma>": [",", " ", "<special_character>", ",,"],
    "<extra>": ["<random_long_string_with_special_characters>"],
    "<invalid_datatype>": ["xsd:invalidDatatype"],
    "<id>": ["<validID>", "<invalidID>"],
    "<validID>": ["_:<letter><letter><letter>"],
    "<invalidID>": [
        "<special_character><special_character><letter><letter><letter><letter>",
        "\"<letter><letter><letter><letter><letter><letter>\"",
        "\"<letter><letter>\\//<letter><letter><letter><letter>\"",
        "<letter>"
    ],
    "<first_name>": ["<valid_first_name>", "<invalid_first_name>"],
    "<valid_first_name>": ["\"Lionel\"", "\"Cristiano\"", "\"Amadou\""],
    "<invalid_first_name>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>",
        "\"\""
    ],
    "<last_name>": ["<valid_last_name>", "<invalid_last_name>"],
    "<valid_last_name>": [
        "\"Messi\"", "\"Ronaldo\"", "\"Fernandes\"", "\"Mbappe\"", "\"O'Neil\"",
        "\"O'Connor\"", "\"Mc'Donald\"", "\"Van der Waals\"", "\"Al-Hassan\"",
        "\"Müller\"", "\"Renée\"", "\"Fiancée\"", "\"D'Artagnan\"", "\"Pérez\"",
        "\"Brontë\"", "\"Núñez\"", "\"Björk\"", "\"Çelik\"", "\"Østergaard\"", "\"Håkon\""
    ],
    "<invalid_last_name>": [
        "\"\"",
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>"
    ],
    "<birthday>": ["\"<validBirthday>\"", "\"<invalid_birthday>\""],
    "<validBirthday>": [
        "19<fiveToNine><digit>-<month>-<day>",
        "20<zeroToTwo><digit>-<month>-<day>"
    ],
    "<fiveToNine>": ["5", "6", "7", "8", "9"],
    "<zeroToTwo>": ["0", "1", "2"],
    "<month>": ["<digit>", "1<digit>"],
    "<day>": ["0<digit>", "1<digit>", "2<digit>"],
    "<invalid_birthday>": [
        "199<random_invalid_digit>-<month>-<day>",
        "202<random_invalid_digit>-<month>-<day>",
        "<random_long_string>",
        "\"\"",
        "9999-99-99",
        "0000-00-00",
        "2020-13-32"
    ],
    "<random_invalid_digit>": ["0", "3", "4", "5", "6", "7", "8", "9"],
    "<year>": ["<valid_year>", "<invalid_year>"],
    "<valid_year>": ["\"2015\"", "\"2016\"", "\"2017\"", "\"2018\"", "\"2019\""],
    "<invalid_year>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>",
        "\"\"",
        "0", "00", "000", "0000", "00000"
    ],
    "<current_club>": ["<valid_current_club>", "<invalid_current_club>"],
    "<valid_current_club>": ["<id>", "<array_of_teams>"],
    "<invalid_current_club>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>"
    ],
    "<marketValue>": ["<valid_marketValue>", "<invalid_marketValue>", "<long_string>"],
    "<valid_marketValue>": [
        "100000000",
        "<digit><digit><digit><digit><digit><digit><digit><digit><digit>",
        "10" * 1000,
        "010"
    ],
    "<invalid_marketValue>": [
        "<random_long_string_with_special_characters>",
        "1million",
        "Millions",
        "\"\""
    ],
    "<position>": ["<valid_position>", "<invalid_position>"],
    "<valid_position>": [
        "\"Forward\"", "\"Midfielder\"", "\"Defender\"", "\"Goalkeeper\"", "\"Striker\"@us"
    ],
    "<invalid_position>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>",
        "\"\""
    ],
    "<countryName>": ["<valid_country>", "<invalid_country>", "<long_string>"],
    "<valid_country>": [
        "\"Argentina\"", "\"Portugal\"", "\"France\"", "\"Egypt\"", "\"England\"@en"
    ],
    "<invalid_country>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>",
        "\"\""
    ],
    "<clubName>": ["<valid_clubName>", "<invalid_clubName>"],
    "<valid_clubName>": [
        "\"Barcelona\"", "\"Juventus\"", "\"Paris Saint-Germain\"@fr", "\"Liverpool\"", "\"Manchester United\""
    ],
    "<invalid_clubName>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>",
        "\"\""
    ],
    "<stadium>": ["<valid_stadium>", "<invalid_stadium>"],
    "<valid_stadium>": [
        "\"Camp Nou\"", "\"Allianz Stadium\"", "\"Parc des Princes\"", "\"Anfield\"", "\"Old Trafford\""
    ],
    "<invalid_stadium>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>",
        "\"\""
    ],
    "<leagueName>": ["<valid_leagueName>", "<invalid_leagueName>"],
    "<valid_leagueName>": [
        "\"La Liga\"", "\"Serie A\"", "\"Ligue 1\"", "\"Premier League\"", "\"Bundesliga\""
    ],
    "<invalid_leagueName>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>",
        "\"\""
    ],
    "<continent>": ["<valid_continent>", "<invalid_continent>"],
    "<valid_continent>": [
        "\"Europe\"", "\"South America\"", "\"Africa\"", "\"Asia\"", "\"North America\"@en"
    ],
    "<invalid_continent>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>",
        "\"\""
    ], 
    "<fifaCode>": ["<valid_fifaCode>", "<invalid_fifaCode>"],
    "<valid_fifaCode>": ["\"ARG\"", "\"POR\"", "\"FRA\"", "\"EGY\"", "\"ENG\""],
    "<invalid_fifaCode>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>",
        "\"\""
    ],
    "<array_of_topTeams>": [
        "( )", "(<valid_team>)", "(<invalid_team>)", "(<valid_team>,<invalid_team>)",
        "(<array_of_topTeams>,<valid_team>)", "(<array_of_topTeams>,<invalid_team>)"
    ],
    "<array_of_teams>": [
        "(<valid_team>)", "(<invalid_team>)", "(<invalid_team>,<array_of_teams>)",
        "(<array_of_teams>)", "(<array_of_teams>,<array_of_teams>)",
        "(<array_of_teams>,<array_of_teams>,(<array_of_teams>))"
    ],
    "<valid_team>": ["<id>", "<id>,<valid_team>"],
    "<invalid_team>": [
        "\"<random_long_string_with_special_characters>\"",
        "\"<random_long_string>\"",
        "\"<special_character_string>\"",
        "\"<random_long_string_with_special_characters>,<invalid_team>\"",
        "(<valid_team>)"
    ],
    "<array_of_topPlayers>": [
        "( )", "(<valid_player>)", "(<invalid_player>)", "(<valid_player>,<invalid_player>)",
        "(<valid_player>,<valid_player>)", "(<invalid_player>,<invalid_player>)",
        "(<valid_player>,<valid_player>,<invalid_player>)", "(<valid_player>,<valid_player>,<valid_team>)",
        "(<invalid_player>,<invalid_player>,<invalid_team>)", "(<valid_player>,<valid_player>,<valid_player>,<invalid_player>)",
        "(<valid_player>,<valid_player>,<valid_player>,<valid_player>)",
        "(<invalid_player>,<invalid_player>,<invalid_player>,<invalid_player>)"
    ],
    "<valid_player>": ["<string>", "<string>,<valid_player>"],
    "<invalid_player>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>"
    ],
    "<array_of_leagues>": [
        "()", "(<valid_league>)", "(<invalid_league>)", "(<valid_league>,<invalid_league>)",
        "(<valid_league>,<valid_league>)", "(<invalid_league>,<invalid_league>)",
        "(<valid_league>,<valid_league>,<invalid_league>)", "(<valid_league>,<valid_league>,<valid_league>)",
        "(<invalid_league>,<invalid_league>,<invalid_league>)", "(<valid_league>,<valid_league>,<valid_league>,<invalid_league>)",
        "(<valid_league>,<valid_league>,<valid_league>,<valid_league>)",
        "(<invalid_league>,<invalid_league>,<invalid_league>,<invalid_league>)"
    ],
    "<valid_league>": ["<id>", "<id>,<valid_league>"],
    "<invalid_league>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>",
        "(This is invalid)",
        "\"Wrong\""
    ],
    "<string>": ["<random_string>", "<random_long_string>"],
    "<random_string>": ["<letter><random_string>", "<digit><random_string>", "<letter>"],
    "<random_long_string>": ["<random_string><random_string>"],
    "<long_string>": ["a", "<long_string> a", "<long_string> <long_string>"],
    "<random_long_string_with_special_characters>": ["<random_string><special_character><random_string>"],
    "<random_special_characters>": ["<special_character>"],
    "<special_character_string>": ["\"<random_special_characters><random_long_string>\""],
    "<special_character>": [
        "<special_character_without_quotes>",
        "<special_character_with_quotes>",
        "<special_character_without_quotes><special_character>",
        "<special_character_with_quotes><special_character>"
    ],
    "<special_character_without_quotes>": [
        "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "-", "_", "=", "+", "[", "]", "{", "}", "|", "\\", ":", ";", "'", "\"", "<", ">", ",", ".", "?", "/", "~", "", " "
    ],
    "<special_character_with_quotes>": [
        "\"!\"", "\"@\"", "\"#\"", "\"$\"", "\"%\"", "\"^\"", "\"&\"", "\"*\"", "\"(\"", "\")\"", "\"-\"", "\"_\"", "\"=\"", "\"+\"", "\"[\"", "\"]\"", "\"{\"", "\"}\"", "\"|\"", "\":\"", "\";\"", "\"'\"", "\",\"", "\".\"", "\"?\"", "\"/\"", "\"~\"", "\"\"", "\" \""
    ],
    "<letter>": list(string.ascii_letters) + ["<letter><letter>"],
    "<digit>": list(string.digits) + ["<digit><digit>"],
    "<xsd:string>": ["xsd:string"],
    "<stadium_name>": ["<valid_stadium_name>", "<invalid_stadium_name>"],
    "<valid_stadium_name>": ["Old Trafford", "Camp Nou", "Allianz Arena", "Santiago Bernabéu"],
    "<invalid_stadium_name>": [
        "<random_long_string_with_special_characters>",
        "<random_long_string>",
        "<special_character_string>"
    ],
}

def write_prefixes(version):
    prefixes = [
        "@prefix ottr: <http://ns.ottr.xyz/0.4/> .\n",
        "@prefix o-rdf: <http://tpl.ottr.xyz/rdf/0.1/> .\n",
        "@prefix foot: <http://example.org/football#> .\n",
        "@prefix schema: <http://schema.org/> .\n",
        "@prefix foaf: <http://xmlns.com/foaf/0.1/> .\n",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n"
    ]
    with open(f'./differential/data/instances/instances{version}.stottr', 'w', encoding='utf-8') as file:
      file.writelines(prefixes)

def main():
    os.makedirs(f'./differential/data/instances', exist_ok=True)
    generated_instances = []
    write_prefixes(args.version)
    instance_file = f'./differential/data/instances/instances{args.version}.stottr'
    for i in range(args.n):
        solver = ISLaSolver(grammar=pyOTTR_GRAMMAR)
        instance = solver.solve()  
        generated_instances.append(instance)
        with open(instance_file, encoding='utf-8') as file:
            file.write(f'{instance} \n')
    print(f"Generated {args.n} batches of instances.")

main()
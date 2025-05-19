from isla.solver import ISLaSolver

grammar = {
    "<start>": ["<instance>"],
    "<instance>": [
        "foot:Footballer(<personIRI>, \"<firstName>\", \"<lastName>\", \"<dateOfBirth>\"^^xsd:date, <currentClub>, <clubHistory>, <marketValue>, \"<position>\", \"<country>\")",
    ],
    "<personIRI>": [
        "<iri>",
        "<blankNode>",
    ],
    "<firstName>": ["<string>", "<string> <firstName>"],
    "<lastName>": ["<string>", "<string> <lastName>"],
    "<dateOfBirth>": ["<date>"],
    "<currentClub>": ["<iri>", "<blankNode>"],
    "<clubHistory>": ["<list>", "<veryLongList>"],
    "<marketValue>": ["<integer>"],
    "<position>": ["<string>", "<string> <position>"],
    "<country>": ["<string>", "<string> <country>"],
    "<list>": [
        "(<itemSequence>)", 
        "(<itemSequence>, <list>)",
        "<nestedList>",
        "<longList>",
    ],
    "<itemSequence>": ["<item>", "<item>, <itemSequence>"],
    "<item>": ["<iri>", "<blankNode>", "<nestedList>"],
    "<nestedList>": [
        "(<item>)",
        "(<item>, <nestedList>)",
    ],
    "<longList>": [
        "(" + ", ".join(["<item>" for _ in range(10)]) + ")"
    ],
    "<veryLongList>": [
        "(" + ", ".join(["<item>" for _ in range(100)]) + ")", 
        "(" + ", ".join(["<nestedList>" for _ in range(40)]) + ")", 
        "(" + ", ".join(["<item>, (<item>, (<item>))" for _ in range(50)]) + ",)"  
    ],
    "<iri>": ["foot:Team<digit>", "foot:League<digit>", "foot:Player<digit>", "_:<letter><letter><letter>"],
    "<blankNode>": ["_:<letter><letter><letter>"],
    "<string>": ["string1", "string2", "string3", "string4", "string5"],
    "<date>": ["2023-01-01", "2023-02-02", "2023-03-03", "2023-04-04", "2023-05-05"],
    "<integer>": ["1", "2", "3", "4", "5"],
    "<digit>": [str(d) for d in range(10)] + ["<digit><digit>"],
    "<letter>": [chr(c) for c in range(ord('a'), ord('z')+1)]
                + [chr(c) for c in range(ord('A'), ord('Z')+1)] + ["<letter><letter>"],
}
constraint = """
forall <instance> inst:
  exists <iri> piri: piri = inst.<personIRI>
  and exists <string> firstName: firstName = inst.<firstName>
  and exists <string> lastName: lastName = inst.<lastName>
  and exists <string> position: position = inst.<position>
  and exists <string> country: country = inst.<country>
  and exists <integer> marketValue: marketValue = inst.<marketValue>
  and str.len(firstName) > 0
  and str.len(lastName) > 0
  and str.len(position) > 0
  and str.len(country) > 0
  and (str.to.int(marketValue) >= 0)
;
"""

solver = ISLaSolver(
    grammar=grammar,
    formula=constraint,
    max_number_free_instantiations=1,
    max_number_smt_instantiations=1,
)

for _ in range(10):
    instance = solver.solve()
    print(instance)
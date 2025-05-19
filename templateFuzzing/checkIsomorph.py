import rdflib
from rdflib.compare import to_isomorphic

def checkIsomorph(file1, file2):
    g1 = rdflib.Graph()
    g2 = rdflib.Graph()
    g1.parse(file1, format='turtle')
    g2.parse(file2, format='turtle')
    
    iso1 = to_isomorphic(g1)
    iso2 = to_isomorphic(g2)
    
    if iso1 == iso2:
        return True
    else:
        return False
    
if __name__ == "__main__":
    file1 = "2templateOUT.ttl"
    file2 = "output_template_2.ttl"
    print(checkIsomorph(file1, file2))

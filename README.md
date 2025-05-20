This is a repository for OTTR fuzzing
Grammars are in generation files and can be adjusted.

For instance fuzzing, the following commands apply as examples, and arguments can be changed:

```bash
cd instanceFuzzing
## Generate instances
python gen_instances.py -n 1000 --iteration 1 -generate yes
## Fine-grained testing of instances
python fineTester.py -input ./data/instances/instances14.stottr
## Metamorphic testing of instances
python morphic.py ./data/instances/instances26.stottr ./football.stottr --iterations 3
## Differential testing (2 commands: one generates, one executes)
python gen_diff_instances.py -n 100 -version 1 -generate yes
python diffTest.py -input_file ./differential/data/diffInstances.py
```

For template fuzzing, as described in Section 3.1.2, the following commands apply:

```bash
cd templateFuzzing
## Generate templates and run the crash oracle
python template_gen.py -n 500 -version 5 -generate yes
## Parse each template individually
python fineTester.py -template ./data/templates/templates5.stottr
## Run differential testing between OTTR engines
python diff_template_test.py --num-templates 10
```

### Combined Fuzzing

The combined fuzzing workflow is described in Section 3.1.3.

To generate both templates and instances for combined fuzzing, use:

```bash
cd combinedFuzz
```
```bash
python combinedFuzz.py -n 500 -version 3 -generate yes
```
To run the combined templates and instances through fine-grained testing, and metamorphic testing is performed on combinations that produce output:
```bash
python fineTester.py -input ./data/templates/templates3.stottr -instance ./data/instances/instances3.stottr
```
To run differential testing on combined fuzzing:
```bash
python diffComb.py --num_templates 10 --num_instances 10
```
(Optional) To search for FATAL errors or others:
```bash
python binarySearcher.py --template ./data/templates/templates3 --anomalyStr "FATAL" --instanceFile ./data/instances/instances3
```

Logs are logged into each scenario's ./logs
Templates, stats, instances and outputs are written to ./data/

import os 

code4ml_path = 'Code4ML_Files'
code_smell_path = 'Nan_Comparison'
java_jar_command = 'java -jar simian-4.0.0.jar'
options_command = '-formatter=yaml -threshold=2'
simian_command = f'{java_jar_command} {options_command} "{code4ml_path}/*.py" "{code_smell_path}/*.py" > result.yaml'

os.system(simian_command)

yaml_content = open('result.yaml', 'r').read()
open('result.yaml', 'w').write(yaml_content.replace('\\', '/'))

def execute_clone_detector()
    pass


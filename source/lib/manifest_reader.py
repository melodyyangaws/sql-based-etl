import yaml
import urllib.request as request
import os.path as path
import sys

def loadYamlRemotely(url, multi_resource=False):
    try:
        fileToBeParsed = request.urlopen(url)
        if multi_resource:
            yaml_data = list(yaml.full_load_all(fileToBeParsed))
        else:
            yaml_data = yaml.full_load(fileToBeParsed) 
        # print(yaml_data)  
    except:
        print("Cannot read yaml config file {}, check formatting."
                "".format(fileToBeParsed))
        sys.exit(1)
        
    return yaml_data 

def loadYamlLocal(yaml_file, multi_resource=False):
    fileToBeParsed=path.join(path.dirname(__file__), yaml_file)
    if not path.exists(fileToBeParsed):
        print("The file {} does not exist"
            "".format(fileToBeParsed))
        sys.exit(1)

    try:
        with open(fileToBeParsed, 'r') as yaml_stream:
            if multi_resource:
                yaml_data = list(yaml.full_load_all(yaml_stream))
            else:
                yaml_data = yaml.full_load(yaml_stream) 
            # print(yaml_data)    
    except:
        print("Cannot read yaml config file {}, check formatting."
                "".format(fileToBeParsed))
        sys.exit(1)
        
    return yaml_data 

# loadYamlLocal('/Users/meloyang/Documents/sourcecode/sql-based-etl/source/app_resources/jupyter-values.yaml')
# loadYamlRemotely('https://raw.githubusercontent.com/kubernetes-sigs/aws-alb-ingress-controller/v1.1.8/docs/examples/alb-ingress-controller.yaml')


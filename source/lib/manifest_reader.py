import yaml
import urllib.request as request
import os.path as path
import sys

def loadManifestYamlRemotely(manifest_url):
    # manifest_url = "https://raw.githubusercontent.com/tripl-ai/deploy/master/kubernetes/argo/hello-world.yaml"
    try:
        fileToBeParsed = request.urlopen(manifest_url)
        yaml_data = yaml.full_load(fileToBeParsed)

    except:
        print("Cannot read yaml config file {}, check formatting."
                "".format(fileToBeParsed))
        sys.exit(1)
        
    return yaml_data 

def loadManifestYamlLocal(yaml_file):
    fileToBeParsed=path.join(path.dirname(__file__), yaml_file)
    if not path.exists(fileToBeParsed):
        print("The file {} does not exist"
            "".format(fileToBeParsed))
        sys.exit(1)

    try:
        with open(fileToBeParsed, 'r') as yaml_stream:
            yaml_data = yaml.full_load(yaml_stream)
    except:
        print("Cannot read yaml config file {}, check formatting."
                "".format(fileToBeParsed))
        sys.exit(1)
        
    return yaml_data 

# loadManifestYamlLocal(r'/Users/meloyang/Documents/sourcecode/sql-based-etl/source/lib/workflow-rbac.yaml')
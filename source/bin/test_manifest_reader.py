import yaml
import sys


# @mock.patch("requests.post")
def test_loadYamlReplaceVarLocal():
    try:
        dataDict = {
            "{{region_name}}": "us-west-2",
            "{{cluster_name}}": "my_cluster",
            "{{vpc_id}}": "testeste12345"
        }
        from bin.manifest_reader import loadYamlReplaceVarLocal
        loadYamlReplaceVarLocal('../app_resources/alb-values.yaml', dataDict)
    except:
        self.fail("Exception can not load the local yaml file with variables")


def test_loadYamlLocal():
    try:
        from bin.manifest_reader import loadYamlLocal
        loadYamlLocal('../app_resources/autoscaler-iam-role.yaml')
    except:
        self.fail("Exception can not load the local yaml file")

def test_loadYamlRemotely():
    try:
        from bin.manifest_reader import loadYamlRemotely
        loadYamlRemotely('https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.1.3/docs/examples/2048/2048_full.yaml',multi_resource=True)
    except:
        self.fail("Exception can not load the remote yaml file")

def test_loadYamlReplaceVarRemotely():
    try:
        dataDict = {
            "{{region_name}}": "us-west-2", 
            "{{cluster_name}}": "my_cluster", 
        }
        from bin.manifest_reader import loadYamlReplaceVarRemotely
        loadYamlReplaceVarRemotely(
            'https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml',
            dataDict, 
            multi_resource=True
        )
    except:
        self.fail("Exception can not load the remote yaml file with variables")



        
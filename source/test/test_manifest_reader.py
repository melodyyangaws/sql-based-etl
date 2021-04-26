######################################################################################################################
# Copyright 2020-2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                      #
#                                                                                                                   #
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance    #
# with the License. A copy of the License is located at                                                             #
#                                                                                                                   #
#     http://www.apache.org/licenses/LICENSE-2.0                                                                    #
#                                                                                                                   #
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES #
# OR CONDITIONS OF ANY KIND, express o#implied. See the License for the specific language governing permissions     #
# and limitations under the License.  																				#                                                                              #
######################################################################################################################

import yaml
import sys
from os import path
from lib.util.manifest_reader import *

curr_dir=path.dirname(path.abspath(__file__))

# @mock.patch("requests.post")
def test_loadyamlreplacevarlocal():
    try:
        data_dict = {
            "{{region_name}}": "us-west-2",
            "{{cluster_name}}": "my_cluster",
            "{{vpc_id}}": "testeste12345"
        }
        load_yaml_replace_var_local(curr_dir+'/../app_resources/alb-values.yaml', data_dict)
    except Exception as e:
        print("Exception can not load the local yaml file with variables:" + str(e))


def test_loadyamllocal():
    try:
        load_yaml_local(curr_dir+'/../app_resources/autoscaler-iam-role.yaml')
    except Exception as e:
        print("Exception can not load the local yaml file" + str(e))

def test_loadyamlremotely():
    try:
        load_yaml_remotely('https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.1.3/docs/examples/2048/2048_full.yaml',multi_resource=True)
    except Exception as e:
        print("Exception can not load the remote yaml file"+ str(e))

def test_loadyamlreplacevarremotely():
    try:
        data_dict = {
            "{{region_name}}": "us-west-2", 
            "{{cluster_name}}": "my_cluster", 
        }
        load_yaml_replace_var_remotely(
            'https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml',
            data_dict, 
            multi_resource=True
        )
    except Exception as e:
        print("Exception can not load the remote yaml file with variables"+ str(e))
     
def test_output_loadyamlreplacevarlocal():
    try:
        finepath=curr_dir+'/../example/test/TEST-cron-job-scheduler.yaml'
        s = load_yaml_replace_var_local(finepath,
            fields={
                    "{{ECR_URL}}": 'TEST'
            })
        print(yaml.dump(s, finepath, default_flow_style=False))

    except Exception as e:
        print("Exception can not load the remote yaml file with variables"+ str(e))
     
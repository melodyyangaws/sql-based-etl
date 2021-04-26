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
import os,sys
import pytest
from aws_cdk.core import App
from lib.spark_on_eks_stack import SparkOnEksStack
from util.interface import SolutionStackSubstitions

@pytest.fixture(scope="session", autouse=True)
def environment():
    os.environ.update(
        {
            "BUCKET_NAME": "mytest",
            "SOLUTION_NAME": "sql-based-etl-with-apache-spark-on-amazon-eks",
            "VERSION": "1.0.0"
        }
    )

@pytest.fixture(scope="session")
def synthesis_cdk(environment):
    app = App(
        runtime_info=False,
        stack_traces=False,
        tree_metadata=False,
        analytics_reporting=False,
        context={
            "BUCKET_NAME": "mytest",
            "SOLUTION_NAME": "sql-based-etl-test",
            "VERSION": "1.0.0",
            "cluster_name": "spark-on-eks-test"
        },
    )
    synthesizer = SolutionStackSubstitions(qualifier="hnb655fds")
    stack = SparkOnEksStack(app, 'SparkOnEKS', 'test_eks', synthesizer=synthesizer)
    root = stack.node.root
    return root.synth(force=True)


@pytest.fixture(scope="session")
def synthesis_solutions(environment):
    app = App(
        runtime_info=False,
        stack_traces=False,
        tree_metadata=False,
        analytics_reporting=False,
        context={
            "BUCKET_NAME": "test",
            "SOLUTION_NAME": "sql-based-etl-with-apache-spark-on-amazon-eks",
            "VERSION": "1.0.0",
            "SOLUTIONS_ASSETS_REGIONAL": "assets-regional",
            "SOLUTIONS_ASSETS_GLOBAL": "assets-global",
        },
    )
    synthesizer = SolutionStackSubstitions(qualifier="hnb655fds")
    stack = SparkOnEksStack(app, 'test', 'test_eks', synthesizer=synthesizer)
    root = stack.node.root
    return root.synth(force=True)

@pytest.fixture(scope="session")
def template_cdk(synthesis_cdk):
    return synthesis_cdk.stacks[0].template


@pytest.fixture(scope="session")
def templates_cdk(synthesis_cdk):
    return synthesis_cdk.stacks

REQUIRED_PARAMETERS = [
    "datalakebucket",
    "jhubuser"
]
@pytest.mark.parametrize("param_name", REQUIRED_PARAMETERS)
def test_parameters(template_cdk, param_name, templates_cdk):
    # these parameters are found, and each has a description
    assert param_name in template_cdk["Parameters"]
    assert template_cdk["Parameters"][param_name][
        "Description"
    ]  # parameter must have a description

def test_no_new_parameters(template_cdk):
    non_asset_parameters = [
        parameter
        for parameter in template_cdk["Parameters"]
        if "AssetParameters" not in parameter and "BootstrapVersion" not in parameter
    ]
    assert len(non_asset_parameters) == len(REQUIRED_PARAMETERS)


def test_jupyter_notebook(template_cdk):
    # jupyter notebook must be in the same region as CFN deployment region, not the CICD pipeline region 
    chart_value = template_cdk["Resources"]["eksclusterEKSchartJHubChartECD30885"]["Properties"]["Values"]['Fn::Join'][1]
    region = ''.join(filter(str.isalnum, str(chart_value[3])))
    assert region == "RefAWSRegion"

def test_stack_description(template_cdk):
    assert template_cdk["Description"].startswith(
        "(SO0141) SQL based ETL with Apache Spark on Amazon EKS"
    )

def test_number_of_subnet(template_cdk):
    # make sure at least 2 private subnets are available
    rsc = template_cdk["Resources"]
    cnt_subnet = [
      rsc[subnet]["Type"] for subnet in rsc if subnet.startswith("networksgeksVpcPrivateSubnet")
    ]
    assert cnt_subnet.count("AWS::EC2::Subnet") >= 2

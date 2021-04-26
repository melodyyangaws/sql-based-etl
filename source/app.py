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

#!/usr/bin/env python3
from aws_cdk import core
from lib.spark_on_eks_stack import SparkOnEksStack
from lib.cloud_front_stack import NestedStack
from os import environ

app = core.App()

eks_name = app.node.try_get_context('cluster_name')
env=core.Environment(account=environ.get("CDK_DEPLOY_ACCOUNT", environ["CDK_DEFAULT_ACCOUNT"]),
                    region=environ.get("AWS_REGION", environ["CDK_DEFAULT_REGION"]))

# Spin up the main stack and a nested stack
eks_stack = SparkOnEksStack(app, 'SparkOnEKS', eks_name, env=env)
# Recommend to remove the CloudFront stack. Setup your own SSL certificate and add it to ALB.
cf_nested_stack = NestedStack(eks_stack,'CreateCloudFront', eks_stack.code_bucket, eks_name, eks_stack.argo_url, eks_stack.jhub_url)

core.Tags.of(eks_stack).add('project', 'sqlbasedetl')
core.Tags.of(cf_nested_stack).add('project', 'sqlbasedetl')

# # Deployment Output
core.CfnOutput(eks_stack,'CODE_BUCKET', value=eks_stack.code_bucket)
core.CfnOutput(eks_stack,'ARGO_URL', value='https://'+ cf_nested_stack.argo_cf)
core.CfnOutput(eks_stack,'JUPYTER_URL', value='https://'+ cf_nested_stack.jhub_cf)

app.synth()


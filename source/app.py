# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
from aws_cdk import core
from bin.config import ConfigSectionMap
from lib.spark_on_eks_stack import SparkOnEksStack
from lib.cloud_front_stack import AddCloudFrontStack
from lib.deploy_pipeline_stack import DeploymentPipeline

app = core.App()

# Get environment vars for 'cdk synth -c env=develop'
target_env = app.node.try_get_context('env')
account = ConfigSectionMap(target_env)['account']
region = ConfigSectionMap(target_env)['region']
env = core.Environment(account=account, region=region)

eks_name = app.node.try_get_context('cluster_name') + '-' + ConfigSectionMap(target_env)['env_str']

# Spin up the main stack
eks_stack = SparkOnEksStack(app, 'SparkOnEKS', eks_name, env=env)
# call an optional nested stack. 
# recommended way is to generate your own certificate, add it to the ALB deployed above
cf_stack = AddCloudFrontStack(eks_stack,'CreateCF', eks_name, eks_stack.argo_url, eks_stack.jhub_url)
# code_pipeline_stack = DeploymentPipeline(app, "Pipeline", env=env)

core.Tags.of(eks_stack).add('project', 'sqlbasedetl')
core.Tags.of(cf_stack).add('project', 'sqlbasedetl')
# core.Tags.of(code_pipeline_stack).add('project', 'sqlbasedetl')

# Deployment Output
core.CfnOutput(eks_stack,'CODE_BUCKET', value=eks_stack.code_bucket)
# core.CfnOutput(eks_stack,'ARGO_ALB_URL', value='http://'+ eks_stack.argo_url+':2746')
# core.CfnOutput(eks_stack,'JUPYTER_ALB_URL', value='http://'+ eks_stack.jhub_url +':8000')
core.CfnOutput(eks_stack,'ARGO_URL', value='https://'+ cf_stack.argo_cf)
core.CfnOutput(eks_stack,'JUPYTER_URL', value='https://'+ cf_stack.jhub_cf)

    

app.synth()

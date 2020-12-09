# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: MIT-0

#!/usr/bin/env python3
from aws_cdk import core
from bin.config import ConfigSectionMap
from lib.spark_on_eks_stack import SparkOnEksStack
# from lib.deploy_pipeline_stack import DeploymentPipeline

app = core.App()

# Get environment vars for 'cdk synth -c env=develop'
target_env = app.node.try_get_context('env')
account = ConfigSectionMap(target_env)['account']
region = ConfigSectionMap(target_env)['region']
env = core.Environment(account=account, region=region)

eks_name = app.node.try_get_context('cluster_name') + '-' + ConfigSectionMap(target_env)['env_str']

# Spin up CDK stacks
eks_stack = SparkOnEksStack(app, 'SparkOnEKS', eks_name, env=env)
# code_pipeline_stack = DeploymentPipeline(app, "PipelineStack", env=env)

core.Tags.of(eks_stack).add('project', 'sqlbasedetl')
# core.Tags.of(code_pipeline_stack).add('project', 'sqlbasedetl')

app.synth()

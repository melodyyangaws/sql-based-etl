#!/usr/bin/env python3
from aws_cdk import core
from lib.config_map import ConfigSectionMap
from sql_based_etl.base_infra_stack import BaseEksInfraStack
from sql_based_etl.etl_app_stack import CreateAppStack

app = core.App()

# Define target environment from input cdk synth -c env=develop
target_env = app.node.try_get_context('env')
account = ConfigSectionMap(target_env)['account']
region = ConfigSectionMap(target_env)['region']
env = core.Environment(account=account, region=region)

cluster_env_name = app.node.try_get_context('cluster_name') + '-' + ConfigSectionMap(target_env)['env_str']

# # Declare stacks using CDK
eks_stack=BaseEksInfraStack(app, 'ekscluster', eksname=cluster_env_name, env=env)
core.Tags.of(eks_stack).add("project", "sqlbasedetl")

# CreateAppStack(app,'etlapps', eks_cluster_stack, env=env)


app.synth()

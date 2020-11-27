import typing

from aws_cdk import (
    core,
    aws_iam as iam,
    # aws_ssm as ssm
)
from typing import  List

class IamConst(core.Construct):

    @property
    def managed_node_role(self):
        return self._managed_node_role

    # @property
    # def fargate_role(self):
    #     return self._fargate_role

    def __init__(self,scope: core.Construct, id:str, cluster_name:str, **kwargs,) -> None:
        super().__init__(scope, id, **kwargs)

# //*********************************************************************//
# //**************************** IAM ROLES ******************************//
# //*********************************************************************//

        # # fargate role
        # _fargate_policy = (
        #     iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKSFargatePodExecutionRolePolicy')
        # )

        # self._fargate_role = iam.Role(self,'fargate-role',
        #     role_name='jhub-fargate-NodeInstanceRole',
        #     assumed_by= iam.ServicePrincipal('eks-fargate-pods.amazonaws.com'),
        #     managed_policies=[_fargate_policy]
        # )
        # core.Tags.of(self._fargate_role).add(
        #     key='eks/%s/type' % cluster_name, 
        #     value='fargate-node'
        # )
        
        # Managed Node Group Instance Role
        _managed_node_managed_policies = (
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKSWorkerNodePolicy'),
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKS_CNI_Policy'),
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2ContainerRegistryReadOnly'),
            iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchAgentServerPolicy'), 
        )
        self._managed_node_role = iam.Role(self,'NodeInstance-Role',
            role_name= cluster_name + '-NodeInstanceRole',
            path='/',
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
            managed_policies=list(_managed_node_managed_policies),
        )
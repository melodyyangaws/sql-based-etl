import typing

from aws_cdk import (
    core,
    aws_iam as iam,
    # aws_ssm as ssm
)
from typing import  List

class IamConst(core.Construct):
    
    @property
    def admin_role(self):
        return self._clusterAdminRole

    @property
    def managed_node_role(self):
        return self._managed_node_role

    # @property
    # def fargate_role(self):
    #     return self._fargate_role

    def __init__(self,scope: core.Construct, id:str, 
        cluster_name:str,
        cluste_admin_name:str, 
        **kwargs,) -> None:

        super().__init__(scope, id, **kwargs)

# //*********************************************************************//
# //**************************** IAM ROLES ******************************//
# //*********************************************************************//

        # EKS admin role
        self._clusterAdminRole = iam.Role(self, 'clusterAdmin',
            role_name= cluste_admin_name,
            assumed_by= iam.AccountRootPrincipal()
        )
        core.Tags.of(self._clusterAdminRole).add(
            key='eks/%s/type' % cluster_name, 
            value='admin-role'
        )

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
                
        # _managed_policy = (
        #     iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKSClusterPolicy'),
        #     iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKSVPCResourceController') 
        # )
        # # control plane role
        # self._control_plane_role = iam.Role(self,'cpRole',
        #     role_name = cluster_name + '-controlplane-role',
        #     assumed_by= iam.ServicePrincipal('eks.amazonaws.com'),
        #     managed_policies=list(_managed_policy),
        # )
        # self._control_plane_role.attach_inline_policy(
        #        iam.Policy(self,"CloudWatchMetrics",
        #         policy_name="CloudWatchMetrics",
        #         statements=[
        #             iam.PolicyStatement(
        #                 actions=["cloudwatch:PutMetricData","cloudwatch:GetMetricData"],
        #                 resources=["*"],
        #             )
        #         ],
        #     )
        # )
        # core.Tags.of(self._control_plane_role).add(
        #     key='eks/%s/type' % cluster_name, 
        #     value='control-plane-role'
        # )

        # # Creating Roles which will be mapped to k8s rbac group with different rights
        # self._eks_admin_team_role = eks_roles(self,'eks-admin',
        #     role_name='eks-admin-team',
        #     k8s_username='admin-team',
        #     k8s_groups=['system:masters'],
        #     cluster_name=cluster_name,
        #     principal=iam.AccountRootPrincipal(),
        # )
        # self._eks_dev_team_role = eks_roles(self,'eks-dev-team',
        #     role_name='eks-dev-team',
        #     k8s_username='dev-team',
        #     k8s_groups=['dev-team'],
        #     cluster_name=cluster_name,
        #     principal=iam.AccountRootPrincipal(),
        # )

        # # Creating Amazon EKS External Secret Role
        # self.external_secrets_role = iam.Role(
        #     scope=self,
        #     id='external-secrets',
        #     role_name=cluster_name+'-external-secrets',
        #     assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
        # )

        # self.external_secrets_role.add_to_policy(
        #     iam.PolicyStatement(
        #         resources=['*'],
        #         actions=['secretsmanager:GetSecretValue', 'secretsmanager:ListSecrets',
        #                  'secretsmanager:GetResourcePolicy', 'secretsmanager:DescribeSecret',
        #                  'secretsmanager:ListSecretVersionIds', 'ssm:GetParameters',
        #                  'ssm:GetParameter', 'ssm:GetParametersByPath',
        #                  'ssm:GetParameterHistory']
        #     )
        # )
 
        # self._cluster.aws_auth.add_masters_role(
        #     role=clusterAdminRole,
        #     username='EKSAdmin'
        # )

        # self._cluster.aws_auth.add_role_mapping(
        #     role=self._eks_admin_team_role, 
        #     groups=['system:masters'],
        #     username='admin-team'
        # )

        # self._cluster.aws_auth.add_role_mapping(
        #     role=self._eks_dev_team_role, 
        #     groups=['dev-team']),
        #     username='dev-team'
        # )

        # ssm.StringParameter(self, 'clusterCert',
        #     string_value=self._cluster.cluster_certificate_authority_data,
        #     description='Cert Authority data of the EKS Cluster' + cluster_name,
        #     parameter_name='/eks/' + cluster_name + '/config/clustercert',
        # )

# def eks_roles(
#     scope: core.Construct,
#     id: str,
#     role_name: str,
#     k8s_username: str,
#     k8s_groups: List[str],
#     cluster_name: str,
#     principal: iam.IPrincipal,
# ) -> iam.IRole:

#     EKSDescribeClusterPolicy = iam.PolicyDocument(
#         statements=[
#             iam.PolicyStatement(
#                 actions=['eks:DescribeCluster'],
#                 resources=['*'],
#             )
#         ]
#     )
#     role = iam.Role(scope,id,
#         path='/eks/',
#         role_name=role_name,
#         assumed_by=principal,
#         inline_policies={
#             'cluster-access': EKSDescribeClusterPolicy
#         }
#     )
#     core.Tags.of(role).add(
#         key='eks/%s/type' % cluster_name,
#         value='user'
#     )
#     core.Tags.of(role).add(
#         key='eks/%s/username' % cluster_name,
#         value=k8s_username,
#     )
   
#     core.Tags.of(role).add(
#         key='eks/%s/groups' % cluster_name,
#         value=','.join(k8s_groups),
#     )

#     return role
        

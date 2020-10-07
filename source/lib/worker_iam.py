import typing

from aws_cdk import (
    core,
    aws_iam as iam,
    aws_ssm as ssm
)


class IamConst(core.Construct):
    @property
    def managed_node_role(self):
        return self._managed_node_role
    @property
    def fargate_role(self):
        return self._fargate_role

    def __init__(self,scope: core.Construct,id: str,cluster_name: str,**kwargs,) -> None:
        super().__init__(scope, id, **kwargs)


        # _managed_node_managed_policies = (
        #     iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKSWorkerNodePolicy'),
        #     iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKS_CNI_Policy'),
        #     iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2ContainerRegistryReadOnly'),
        # )
        # _fargate_managed_policies = (
        #     iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKSFargatePodExecutionRolePolicy'),
        # )

        # self._managed_node_role = iam.Role(self,'worker-role',
        #     role_name= cluster_name + '-worker-role',
        #     path='/eks/',
        #     assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
        #     managed_policies=list(_managed_node_managed_policies),
        # )
        
        # self._managed_node_role.add_to_policy(
        #     iam.PolicyStatement(
        #         resources=['*'],
        #         actions=['secretsmanager:GetSecretValue']
        #     )
        # )
        # core.Tags.of(self._managed_node_role).add(
        #     key='eks/%s/type' % cluster_name,
        #     value='managed-node'
        # )

        # self._fargate_role = iam.Role(self,'fargate-role',
        #     role_name=cluster_name + '-fargate-worker-role',
        #     path='/eks/',
        #     assumed_by=iam.ServicePrincipal('eks-fargate-pods.amazonaws.com'),
        #     managed_policies=list(_fargate_managed_policies)
        # )

        # core.Tags.of(self._fargate_role).add(
        #     key='eks/%s/type' % cluster_name,
        #     value='fargate-node'
        # )

        # # Store roles and SG to parameter store for other stack use
        # ssm.StringParameter(self, 'workerRole',
        #     description='The EKS ' + cluster_name + 'Worker role name',
        #     string_value=self._eks_worker_role.role_arn,
        #     parameter_name='/eks/' + cluster_name + '/workerRoleName'
        # )
        # # Creating Amazon EKS External Secret Role
        # self.external_secrets_role = iam.Role(
        #     scope=self,
        #     id='external-secrets',
        #     role_name=id + '-external-secrets',
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

 

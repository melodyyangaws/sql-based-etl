import typing

from aws_cdk import (
    core,
    aws_iam as iam,
    aws_ssm as ssm
)

_eks_worker_role_base_policies = (
    iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKSWorkerNodePolicy'),
    iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKS_CNI_Policy'),
    iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2ContainerRegistryReadOnly'),
)


class IamStack(core.Construct):
    @property
    def worker_role(self):
        return self._eks_worker_role

    def __init__(
            self,
            scope: core.Construct,
            id: str,
            cluster_name: str,
            **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self._eks_worker_role = iam.Role(self,'worker-role',
            role_name=cluster_name + '-work-role',
            path='/eks/',
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
            managed_policies=list(_eks_worker_role_base_policies),
        )

        self._eks_worker_role.add_to_policy(
            iam.PolicyStatement(
                resources=['*'],
                actions=['secretsmanager:GetSecretValue']
            )
        )
        core.Tags.of(self._eks_worker_role).add(
            key='eks/%s/type' % cluster_name,
            value='node'
        )
        # Store roles and SG to parameter store for other stack use
        ssm.StringParameter(self, 'workerRole',
            description='The EKS ' + cluster_name + 'Worker role name',
            string_value=self._eks_worker_role.role_arn,
            parameter_name='/eks/' + cluster_name + '/workerRoleName'
        )
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

 

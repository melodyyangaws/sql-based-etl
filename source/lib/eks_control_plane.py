from aws_cdk import (
    core,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_eks as eks,
    aws_ec2 as ec2,
)
from typing import List

class EksConst(core.Construct):
    @property
    def cluster(self):
        return self._cluster

    def __init__(
            self,
            scope: core.Construct,
            id: str,
            cluster_name: str,
            cluster_vpc: ec2.IVpc,   
            cluster_sg: ec2.ISecurityGroup,
            cluster_version: eks.KubernetesVersion,
            **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        
                    
# //*********************************************************************//
# //**************************** IAM ROLES ******************************//
# //*********************************************************************//

        # Creating Amazon EKS Cluster Role
        _managed_policy = (
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKSClusterPolicy'),
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKSVPCResourceController') 
        )

        self._eks_control_plane_role = iam.Role(self,'eksRole',
            role_name = cluster_name + '-cluster-role',
            assumed_by= iam.ServicePrincipal('eks.amazonaws.com'),
            managed_policies=list(_managed_policy),
        )
        self._eks_control_plane_role.attach_inline_policy(
               iam.Policy(self,"CloudWatchMetrics",
                policy_name="CloudWatchMetrics",
                statements=[
                    iam.PolicyStatement(
                        actions=["cloudwatch:PutMetricData","cloudwatch:GetMetricData"],
                        resources=["*"],
                    )
                ],
            )
        )

        clusterAdminRole = iam.Role(self, 'clusterAdmin',
            role_name='EKSAdmin',
            assumed_by= iam.AccountRootPrincipal()
        )

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

        
# //*********************************************************************//
# //************************* EKS Cluster *******************************//
# //*********************************************************************//
# 
        self._cluster = eks.Cluster(self,'ekscluster',
                vpc=cluster_vpc,
                role=self._eks_control_plane_role,
                cluster_name=cluster_name,
                masters_role=clusterAdminRole,
                version=cluster_version,
                endpoint_access=eks.EndpointAccess.PUBLIC_AND_PRIVATE,
                security_group=cluster_sg,
                default_capacity=0
        )
  
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

def eks_roles(
    scope: core.Construct,
    id: str,
    role_name: str,
    k8s_username: str,
    k8s_groups: List[str],
    cluster_name: str,
    principal: iam.IPrincipal,
) -> iam.IRole:

    EKSDescribeClusterPolicy = iam.PolicyDocument(
        statements=[
            iam.PolicyStatement(
                actions=['eks:DescribeCluster'],
                resources=['*'],
            )
        ]
    )
    role = iam.Role(scope,id,
        path='/eks/',
        role_name=role_name,
        assumed_by=principal,
        inline_policies={
            'cluster-access': EKSDescribeClusterPolicy
        }
    )
    core.Tags.of(role).add(
        key='eks/%s/type' % cluster_name,
        value='user'
    )
    core.Tags.of(role).add(
        key='eks/%s/username' % cluster_name,
        value=k8s_username,
    )
   
    core.Tags.of(role).add(
        key='eks/%s/groups' % cluster_name,
        value=','.join(k8s_groups),
    )

    return role
        
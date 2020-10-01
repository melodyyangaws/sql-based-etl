from aws_cdk import (
    core,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_eks as eks,
    aws_ec2 as ec2
)
from typing import List

class EksStack(core.Construct):
    @property
    def cluster(self):
        return self._cluster

    def __init__(
            self,
            scope: core.Construct,
            id: str,
            cluster_name: str,
            cluster_vpc: ec2.IVpc,   
            cluster_version: eks.KubernetesVersion,
            **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        
                    
# //*********************************************************************//
# //****************************  ROLES *********************************//
# //*********************************************************************//

        # Creating Amazon EKS Cluster Role
        managed_policy = iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKSClusterPolicy')
        principal = iam.AccountRootPrincipal()

        self._eks_control_plane_role = iam.Role(self,'eksRole',
            role_name = cluster_name + '-cluster-role',
            assumed_by= iam.ServicePrincipal('eks.amazonaws.com'),
            managed_policies=[managed_policy],
        )

        # Creating Roles which will be mapped to k8s rbac group with different rights
        self._eks_admin_team_role = eks_roles(self,'eks-admin-team',
            role_name='eks-admin-team',
            k8s_username='admin',
            k8s_groups=['system:masters'],
            cluster_name=cluster_name,
            principal=principal,
        )

        self._eks_dev_team_role = eks_roles(self,'eks-dev-team',
            role_name='eks-dev-team',
            k8s_username='dev-team',
            k8s_groups=['dev-team'],
            cluster_name=cluster_name,
            principal=principal,
        )

        self._eks_dev_team_advanced_role = eks_roles(self,'eks-dev-team-advanced',
            role_name='eks-dev-team-advanced',
            k8s_username='dev-team-advanced',
            k8s_groups=['dev-team-advanced'],
            cluster_name=cluster_name,
            principal=principal,
        )

       
# //*********************************************************************//
# //************************* EKS Cluster *******************************//
# //*********************************************************************//
# 
        self._cluster = eks.Cluster(self,'ekscluster',
                vpc=cluster_vpc,
                role=self._eks_control_plane_role,
                cluster_name=cluster_name,
                version=cluster_version,
                # endpoint_access=eks.EndpointAccess.PRIVATE,
                default_capacity=0
        )
  
        self._cluster.aws_auth.add_masters_role(self._eks_admin_team_role)
        
        self._cluster.aws_auth.add_role_mapping(
            role=self._eks_dev_team_role, 
            groups=['dev-team'])
      
        self._cluster.aws_auth.add_role_mapping(
            role=self._eks_dev_team_advanced_role,
            groups=['dev-team-advanced'])
      
        ssm.StringParameter(self, 'clusterCert',
            string_value=self._cluster.cluster_certificate_authority_data,
            description='Cert Authority data of the EKS Cluster' + cluster_name,
            parameter_name='/eks/' + cluster_name + '/config/clustercert',
        )
        
        ssm.StringParameter(self, 'clusterNameParam',
            string_value=self._cluster.cluster_endpoint,
            description='EKS Cluster endpoint ' + cluster_name,
            parameter_name='/eks/' + cluster_name + '/config/endpoint'
        )


def eks_roles(
    scope: core.Construct,
    id: str,
    role_name: str,
    k8s_username: str,
    k8s_groups: List[str],
    cluster_name: str,
    principal: iam.IPrincipal,
) -> iam.IRole:

    cluster_access = iam.PolicyDocument(
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
            'cluster-access': cluster_access
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
        
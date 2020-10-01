from aws_cdk import core
from aws_cdk.aws_eks import KubernetesVersion
from sql_based_etl.eks_control_plane import EksStack
from sql_based_etl.iam import IamStack
from sql_based_etl.network_sg import NetworkSgStack

class BaseEksStack(core.Stack):

    def __init__(self, scope: core.Construct, 
    id: str, 
    eksname: str,
    # tags: str,
    **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        network_sg_stack = NetworkSgStack(self,'network-sg-stack',eksname)
        iam_stack = IamStack(self,'iam-stack',eksname)

        eks_cluster_stack = EksStack(self,'eks-cluster-stack',
            cluster_name = eksname,
            cluster_vpc = network_sg_stack.vpc,
            cluster_version = KubernetesVersion.V1_17
        )
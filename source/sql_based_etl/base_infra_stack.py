from aws_cdk import (
    core,
    aws_ec2 as ec2,
    aws_eks as eks,
    aws_autoscaling as asg,
    aws_cloud9 as cloud9
)
from lib.eks_control_plane import EksConst
from lib.network_sg import NetworkSgConst
from lib.worker_node import WorkerNodeConst

class BaseEksInfraStack(core.Stack):
    # @property
    # def cluster(self):
    #     return eks_construct

    def __init__(self, scope: core.Construct, id: str, eksname: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self._network_sg_construct = NetworkSgConst(self,'network-sg-stack',eksname)
        
        eks_construct = EksConst(self,'create-eks-cluster',
            cluster_name = eksname,
            cluster_vpc = self._network_sg_construct.vpc,
            cluster_sg= self._network_sg_construct.cluster_sg,
            cluster_version = eks.KubernetesVersion.V1_17
        )

        WorkerNodeConst(self,'add-worker-node',eks_construct)

# //*********************************************************************//
# //****************** Cloud9 for Private EKS cluster ********************//
# //*********************************************************************//
# 
        # # create a cloud9 ec2 environment in a new VPC
        # c9env = cloud9.Ec2Environment(self, 'Cloud9Env',
        #     vpc=self._network_sg_construct.vpc,
        #     instance_type=ec2.InstanceType('t3.small'),
        #     subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        # )

        # # print the Cloud9 IDE URL in the output
        # core.CfnOutput(self, 'URL', value=c9env.ide_url)



from aws_cdk import (
    core,
    aws_eks as eks,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_ec2 as ec2
)
from lib.eks_control_plane import EksConst

class CreateAppStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, cluster_stack: EksConst, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # # Get Cluster SecurityGroup from SSM
        # self._eks_cluster_sg = ec2.SecurityGroup.from_security_group_id(
        #     scope=self,
        #     id='clusterSecurityGroupId',
        #     security_group_id=(ssm.StringParameter.from_string_parameter_name(
        #         scope=self,
        #         id='clusterSgParam',
        #         string_parameter_name= '/eks/' + cluster_name + '/securityGroupId').string_value
        #     )
        # )
        
        # Creating AutoScaling Group to host containers on EC2
        cluster_stack.add_chart(self,'argo-chart',
            chart='argo',
            repository='https://argoproj.github.io/argo-helm',
            release='argo',
            namespace='argo')

        # self.managedNodegroup=eks_cluster.add_manifest()
        # self.workerNodegroupAsg = asg.AutoScalingGroup(
        #     scope=self, 
        #     id='EksWorkerNodeGroup', 
        #     vpc=cluster_vpc,
        #     instance_type=ec2.InstanceType('r5.large'),
        #     desired_capacity= desired_node_count,
        #     machine_image=eks.EksOptimizedImage(
        #         kubernetes_version=cluster_version,
        #         node_type=eks.NodeType.STANDARD
        #     ),
        #     min_capacity=0,
        #     max_capacity=3,
        #     role=worker_role,
        #     update_type=asg.UpdateType.ROLLING_UPDATE
        # )

        # self.workerNodegroupAsg.connections.allow_from(
        #     other=cluster_sg,
        #     port_range=ec2.Port.tcp_range(start_port=1025, end_port=65535),
        # )

        # self.workerNodegroupAsg.connections.allow_from(
        #     other=cluster_sg,
        #     port_range=ec2.Port.tcp(443)
        # )
        # self.workerNodegroupAsg.connections.allow_internally(port_range=ec2.Port.all_traffic())
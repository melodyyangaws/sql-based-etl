from aws_cdk import (
    core,
    aws_ec2 as ec2
)
class NetworkSgConst(core.Construct):

    @property
    def vpc(self):
        return self._vpc
        
    @property
    def efs_sg(self):
        return self._eks_efs_sg    

    def __init__(self,scope: core.Construct, id:str, eksname:str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
# //*************************************************//
# //******************* NETWORK ********************//
# //************************************************//
        # create VPC
        self._vpc = ec2.Vpc(self, 'eksVpc',max_azs=2)
        core.Tags.of(self._vpc).add('Name', eksname + 'EksVpc')

        # VPC endpoint security group
        self._vpc_endpoint_sg = ec2.SecurityGroup(self,'EndpointSg',
            security_group_name=eksname + '-EndpointSg',
            vpc=self._vpc,
            description='Security Group for Endpoint',
        )
        self._vpc_endpoint_sg.add_ingress_rule(ec2.Peer.ipv4(self._vpc.vpc_cidr_block),ec2.Port.tcp(port=443))
        core.Tags.of(self._vpc_endpoint_sg).add('Name',eksname+'VpcEndpointSG')

        # Add VPC endpoint 
        self._vpc.add_gateway_endpoint("S3GatewayEndpoint",
                                        service=ec2.GatewayVpcEndpointAwsService.S3,
                                        subnets=[ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
                                                 ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE)])
                                                      
        _ecr_ep=self._vpc.add_interface_endpoint("EcrDockerEndpoint",service=ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER, security_groups=[self._vpc_endpoint_sg])
        _ec2_ep=self._vpc.add_interface_endpoint("Ec2Endpoint", service=ec2.InterfaceVpcEndpointAwsService.EC2,security_groups=[self._vpc_endpoint_sg])
        _cw_ep=self._vpc.add_interface_endpoint("CWLogsEndpoint", service=ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS,security_groups=[self._vpc_endpoint_sg])
        # _sts_ep=self._vpc.add_interface_endpoint("StsEndpoint", service=ec2.InterfaceVpcEndpointAwsService.STS,security_groups=[self._vpc_endpoint_sg])

# //******************************************************//
# //******************* SECURITY GROUP ******************//
# //****************************************************//
        # EFS sg
        self._eks_efs_sg = ec2.SecurityGroup(self,'EFSSg',
            security_group_name=eksname + '-EFS-sg',
            vpc=self._vpc,
            description='NFS access to EFS from EKS worker nodes',
        )
        self._eks_efs_sg.add_ingress_rule(self._eks_efs_sg,ec2.Port.tcp(port=2049))

        core.Tags.of(self._eks_efs_sg).add('kubernetes.io/cluster/' + eksname,'owned')
        core.Tags.of(self._eks_efs_sg).add('Name',eksname+'EFS-sg')

        # self._eks_control_plane_sg = ec2.SecurityGroup(self,'control-plane-sg',
        #     security_group_name= eksname + '-control-plane-sg',
        #     vpc=self._vpc,
        #     allow_all_outbound=True,
        #     description='EKS control plane SG for' + eksname,
        # )
        # core.Tags.of(self._eks_control_plane_sg).add('kubernetes.io/cluster/' + eksname,'owned')
        # core.Tags.of(self._eks_control_plane_sg).add('Name','control-plane-sg')

        # # worker SG
        # self._eks_worker_sg = ec2.SecurityGroup(self,'worker-sg',
        #     security_group_name= eksname + '-worker-sg',
        #     vpc=self._vpc,
        #     allow_all_outbound=True,
        #     description='EKS worker SG for ' + eksname,
        # )
        # core.Tags.of(self._eks_worker_sg).add('kubernetes.io/cluster/' + eksname,'owned')
        # core.Tags.of(self._eks_worker_sg).add('Name', eksname + '-worker-sg')
        
        # # SG Ports

        # self._eks_control_plane_sg.add_ingress_rule(self._eks_worker_sg,ec2.Port.all_traffic())
        # self._eks_control_plane_sg.add_ingress_rule(self._eks_control_plane_sg,ec2.Port.all_traffic())
        # self._eks_control_plane_sg.add_ingress_rule(self._eks_worker_sg,ec2.Port.tcp(port=443))
        # self._eks_control_plane_sg.add_ingress_rule(self._eks_worker_sg,ec2.Port.tcp(port=10250)


        # self._eks_worker_sg.add_ingress_rule(self._eks_worker_sg,ec2.Port.all_traffic())
        # self._eks_worker_sg.add_ingress_rule(self._eks_control_plane_sg,ec2.Port.all_traffic())

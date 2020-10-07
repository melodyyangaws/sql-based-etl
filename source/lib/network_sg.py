#!/usr/bin/env python3
from aws_cdk import (
    core,
    aws_ssm as ssm
)
from aws_cdk.aws_ec2 import (
    Vpc, 
    Port,
    SecurityGroup,
    SubnetSelection, 
    SubnetType, 
    GatewayVpcEndpointAwsService, 
    InterfaceVpcEndpointAwsService
)

class NetworkSgConst(core.Construct):

    @property
    def vpc(self):
        return self._vpc

    @property
    def cluster_sg(self):
        return self._eks_control_plane_sg

    def __init__(
            self,
            scope: core.Construct,
            id: str,
            cluster_name: str,
            **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # create a vpc
        self._vpc = Vpc(self, 'eksVpc',max_azs=2)

        core.Tags.of(self._vpc).add(
                key='Name',
                value= cluster_name + 'eksVpc',
        )

        # Add VPC endpoint 
        self._vpc.add_gateway_endpoint("S3GatewayEndpoint",
                                        service=GatewayVpcEndpointAwsService.S3,
                                        subnets=[SubnetSelection(subnet_type=SubnetType.PUBLIC),
                                                 SubnetSelection(subnet_type=SubnetType.PRIVATE)])
                                                      
        # self._vpc.add_interface_endpoint("EcrDockerEndpoint", 
        #                                 service=InterfaceVpcEndpointAwsService.ECR_DOCKER
        # )
        self._vpc.add_interface_endpoint("Ec2Endpoint", 
                                        service=InterfaceVpcEndpointAwsService.EC2
        )
        self._vpc.add_interface_endpoint("CWLogsEndpoint", 
                                        service=InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS
        )
        self._vpc.add_interface_endpoint("StsEndpoint", 
                                        service=InterfaceVpcEndpointAwsService.STS
        )

        # # Fetch vpc
        # self.vpc = aws_ec2.Vpc.from_lookup(
        #     self,
        #     'Vpc',
        #     vpc_id=vpc_id,
        # )

        # Control plane SG
        self._eks_control_plane_sg = SecurityGroup(self,'control-plane-sg',
            security_group_name= cluster_name + '-control-plane-sg',
            vpc=self._vpc,
            allow_all_outbound=True,
            description='EKS control plane SG for' + cluster_name,
        )
        core.Tags.of(self._eks_control_plane_sg).add(
                key='kubernetes.io/cluster/' + cluster_name,
                value= 'owned',
        )
        core.Tags.of(self._eks_control_plane_sg).add(
                key='Name',
                value= 'control-plan-sg',
        )

        # worker SG
        self._eks_worker_sg = SecurityGroup(self,'worker-sg',
            security_group_name= cluster_name + '-worker-sg',
            vpc=self._vpc,
            allow_all_outbound=True,
            description='EKS worker SG for '+ cluster_name,
        )

        core.Tags.of(self._eks_worker_sg).add(
                key='kubernetes.io/cluster/' + cluster_name,
                value= 'owned',
        )
        core.Tags.of(self._eks_worker_sg).add(
                key='Name',
                value= cluster_name+ '-worker-sg',
        )

         # Allow ports from workers to control plane
        self._eks_control_plane_sg.add_ingress_rule(
            peer=self._eks_worker_sg,
            connection=Port.all_traffic(),
        )
        self._eks_control_plane_sg.add_ingress_rule(
            peer=self._eks_control_plane_sg,
            connection=Port.all_traffic(),
        )
        # self._eks_control_plane_sg.add_ingress_rule(
        #     peer=self._eks_worker_sg,
        #     connection=Port.tcp(port=443),
        # )
        # self._eks_control_plane_sg.add_ingress_rule(
        #     peer=self._eks_worker_sg,
        #     connection=Port.tcp(port=10250),
        # )

        # # Allow ports from control plan to workers
        # self._eks_control_plane_sg.add_egress_rule(
        #     peer=self._eks_worker_sg,
        #     connection=Port.tcp_range(start_port=1025, end_port=65535)
        # )
        # self._eks_control_plane_sg.add_egress_rule(
        #     peer=self._eks_worker_sg,
        #     connection=Port.tcp(port=443),
        # )
        # self._eks_control_plane_sg.add_egress_rule(
        #     peer=self._eks_worker_sg,
        #     connection=Port.tcp(port=10250),
        # )

        # Allow ports 0-65535 from control plane to workers
        # self._eks_worker_sg.add_ingress_rule(
        #     peer=self._eks_control_plane_sg,
        #     connection=Port.tcp_range(start_port=0, end_port=65535),
        # )
        # self._eks_worker_sg.add_ingress_rule(
        #     peer=self._eks_control_plane_sg,
        #     connection=Port.tcp(port=10250),
        # )
        self._eks_worker_sg.add_ingress_rule(
            peer=self._eks_worker_sg,
            connection=Port.all_traffic(),
        )
        self._eks_worker_sg.add_ingress_rule(
            peer=self._eks_control_plane_sg,
            connection=Port.all_traffic(),
        )
        # self._eks_worker_sg.add_egress_rule(
        #     connection=Port.all_traffic()
        # )
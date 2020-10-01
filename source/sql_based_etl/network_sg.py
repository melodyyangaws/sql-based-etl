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

class NetworkSgStack(core.Construct):

    @property
    def vpc(self):
        return self._vpc
    
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

        # Add S3 VPC endpoint 
        self._vpc.add_gateway_endpoint("S3GatewayEndpoint",
                                        service=GatewayVpcEndpointAwsService.S3,
                                        subnets=[SubnetSelection(subnet_type=SubnetType.PUBLIC),
                                                 SubnetSelection(subnet_type=SubnetType.PRIVATE)])
                                                      
        # Add ECR VPC endpoints
        self._vpc.add_interface_endpoint("EcrDockerEndpoint", 
                                        service=InterfaceVpcEndpointAwsService.ECR_DOCKER
        )
        self._vpc.add_interface_endpoint("SSMEndpoint", 
                                        service=InterfaceVpcEndpointAwsService.SSM
        )
        # )
        # # Fetch vpc
        # self.vpc = aws_ec2.Vpc.from_lookup(
        #     self,
        #     'Vpc',
        #     vpc_id=vpc_id,
        # )

        # # Fetch Subnets
        # self.subnet_a_eks = aws_ec2.Subnet.from_subnet_attributes(self, 'subnetaeks',
        #                                                           availability_zone=scope.region + 'a',
        #                                                           subnet_id=aws_ssm.StringParameter.value_from_lookup(
        #                                                                self, "/config/network/subnetaeks")
        #                                                           )
        # self.subnet_b_eks = aws_ec2.Subnet.from_subnet_attributes(self, 'subnetbeks',
        #                                                           availability_zone=scope.region + 'b',
        #                                                           subnet_id=aws_ssm.StringParameter.value_from_lookup(
        #                                                                self, "/config/network/subnetbeks")
        #                                                          )


        # Control plane SG
        self._eks_control_plane_sg = SecurityGroup(self,'control-plane-sg',
            security_group_name= cluster_name + '-master-sg',
            vpc=self._vpc,
            allow_all_outbound=False,
            description='EKS control plane SG for' + cluster_name
        )

        # worker SG
        self._eks_worker_sg = SecurityGroup(self,'worker-sg',
            security_group_name= cluster_name + '-worker-sg',
            vpc=self._vpc,
            # allow_all_outbound=True,
            description='EKS worker SG for '+ cluster_name,
        )

        # Add inbound & outbound roles
        self._eks_worker_sg.add_ingress_rule(
            peer=self._eks_worker_sg,
            connection=Port.all_traffic(),
        )

        # Allow ports 0-65535 from control plane to workers
        self._eks_worker_sg.add_ingress_rule(
            peer=self._eks_control_plane_sg,
            connection=Port.tcp_range(start_port=0, end_port=65535),
        )

        # Allow port 443,80 from workers to control plane
        self._eks_control_plane_sg.add_ingress_rule(
            peer=self._eks_worker_sg,
            connection=Port.tcp(port=443),
        )
        self._eks_control_plane_sg.add_ingress_rule(
            peer=self._eks_worker_sg,
            connection=Port.tcp(port=80),
        )

        # Allow ports 0-65535 from control plan out to worker
        self._eks_control_plane_sg.add_egress_rule(
            peer=self._eks_worker_sg,
            connection=Port.tcp_range(start_port=0, end_port=65535),
        )

        # ssm.StringParameter(self,'control plan sg',
        #     description= cluster_name + 'Security Group ID',
        #     string_value=self._eks_control_plane_sg.security_group_id,
        #     parameter_name='/eks/' + cluster_name + '/control-plane-sg'
        # )

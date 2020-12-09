from aws_cdk import (
    core,
    aws_eks as eks,
    aws_ec2 as ec2,
    # aws_efs as efs
)
from aws_cdk.aws_iam import IRole

class EksConst(core.Construct):

    @property
    def my_cluster(self):
        return self._my_cluster

    def __init__(self,scope: core.Construct, id:str, eksname: str, eksvpc: ec2.IVpc, noderole: IRole, **kwargs,) -> None:
        super().__init__(scope, id, **kwargs)

# //**********************************************************************//
# //******************* EKS CLUSTER WITH NO NODE GROUP *******************//
# //*********************************************************************//
        self._my_cluster = eks.Cluster(self,'EksCluster',
                vpc= eksvpc,
                cluster_name=eksname,
                output_cluster_name=True,
                version= eks.KubernetesVersion.V1_18,
                endpoint_access= eks.EndpointAccess.PUBLIC_AND_PRIVATE,
                default_capacity=0
        )

# //***********************************************************************//
# //********************* MANAGED NODE GROUP IN EKS *************************//
# //***************  compute resource to run Spark jobs *******************//
# //*********************************************************************//

        _managed_node = self._my_cluster.add_nodegroup_capacity('managed-nodegroup',
            nodegroup_name = 'etl-job',
            node_role = noderole,
            desired_size = 1,
            max_size = 5,
            min_size = 1,
            disk_size = 50,
            instance_type = ec2.InstanceType('r5.xlarge'),
            labels = {'app':'spark', 'lifecycle':'OnDemand'},
            subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE,one_per_az=True)
        )
        core.Tags.of(_managed_node).add('Name','ManagedNode'+eksname)            
# //****************************************************************************************//
# //*********************** Add Spot NodeGroup to EKS *************************************//
# //************* Run Spark driver on reliable on-demand, exectutor on spot **************//
# //************ CDK automatically installs the spot interrupt handler daemon ***********//
# //******************  to handle EC2 Spot Instance Termination Notices.****************//
# //***********************************************************************************//

        _spot_node = self._my_cluster.add_auto_scaling_group_capacity('spot',
            instance_type=ec2.InstanceType('r4.xlarge'),
            min_capacity=1,
            max_capacity=10,
            spot_price='1'
        )
        _spot_node.add_security_group(
            ec2.SecurityGroup.from_security_group_id(self, 'sharedNodeSG', 
                self._my_cluster.cluster_security_group_id
            )
        )
        # add auto scaler to the cluster 
        core.Tags.of(_spot_node).add('Name', 'Spot-'+eksname)
        core.Tags.of(_spot_node).add('k8s.io/cluster-autoscaler/enabled', 'true')
        core.Tags.of(_spot_node).add('k8s.io/cluster-autoscaler/'+eksname, 'owned')


# //*********************************************************************//
# //******************** ADD EFS PERSISTENT STORAGE *********************//
# //*********** enable S3A staging commiter for faster S3 access ********//
# //*********************************************************************//
        # _csi_driver_chart = self._my_cluster.add_helm_chart('EFSDriver', 
        #     chart='aws-efs-csi-driver',
        #     release='efs',
        #     repository='https://github.com/kubernetes-sigs/aws-efs-csi-driver/releases/download/v0.3.0/helm-chart.tgz',
        #     create_namespace=False,
        #     namespace='kube-system',
        # )

        # _k8s_efs = efs.FileSystem(self,'EFSFileSystem',
        #     vpc=eksvpc,
        #     encrypted=True,
        #     file_system_name='efs-quickaccess',
        #     lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,
        #     performance_mode=efs.PerformanceMode.MAX_IO,
        #     removal_policy=core.RemovalPolicy.DESTROY,
        #     vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE, one_per_az=True)
        # )
        # _efs_mount_target = efs.CfnMountTarget(self,'MountEFS',
        #     file_system_id=_k8s_efs.file_system_id,
        #     security_groups=[eks_efs_sg.security_group_id],
        #     subnet_id=eksvpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE).subnet_ids[0]
        # )
        # _pv= eks.KubernetesManifest(self,'pvClaim',
        #     cluster=self._my_cluster,
        #     manifest=loadYamlReplaceVarLocal('../app_resources/efs-spec.yaml', 
        #         fields= {
        #             "{{FileSystemId}} ": _k8s_efs.file_system_id
        #         },
        #         multi_resource=True)
        # )      
        # _pv.node.add_dependency(_k8s_efs)
from aws_cdk import (
    core,
    aws_eks as eks,
    aws_ec2 as ec2,
)
from aws_cdk.aws_iam import (
    PolicyStatement as policy,
    ManagedPolicy,
    ServicePrincipal,
    Role
)
from bin.manifest_reader import *

class NativeSparkStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, eksname: str, admin_name: str, bucket_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

# # //*************************************************************************************//
# # //************ Create service account for native Spark jobs  **************************//
# # //***********************************************************************************//
        _spark_sa = self._my_cluster.add_service_account('nativeSparkSa',
            name='nativejob',
            namespace='spark'
        )
        _spark_sa.node.add_dependency(_etl_ns)

        _setting = {"{{MY_SA}}": _spark_sa.service_account_name}
        _spark_rb = self._my_cluster.add_manifest('sparkRoleBinding',
            loadYamlReplaceVarLocal('../app_resources/native-spark-rbac.yaml',fields= _setting)
        )
        _spark_rb.node.add_dependency(_spark_sa)

        _setting={"{{codeBucket}}": code_bucket}
        _spark_iam = loadYamlReplaceVarLocal('../app_resources/native-spark-iam-role.yaml',fields=_setting)
        for statmnt in _spark_iam:
            _spark_sa.add_to_principal_policy(iam.PolicyStatement.from_json(statmnt))

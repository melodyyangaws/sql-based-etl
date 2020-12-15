from aws_cdk import (
    core, 
    aws_s3 as s3,
    aws_s3_deployment as s3deploy
)

class S3AppCodeConst(core.Construct):

    @property
    def code_bucket(self):
        return self._code_bucket

    def __init__(self,scope: core.Construct, id: str, **kwargs,) -> None:
        super().__init__(scope, id, **kwargs)

       # Upload application code to S3 bucket 
        artifact_bucket=s3.Bucket(self, id, 
            encryption=s3.BucketEncryption.KMS_MANAGED
        )  
        s3deploy.BucketDeployment(self, "DeployCode",
            sources=[s3deploy.Source.asset("deployment/app_code")],
            destination_bucket= artifact_bucket,
            destination_key_prefix="app_code"
        )
        self._code_bucket = artifact_bucket.bucket_name

# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: MIT-0
import setuptools

with open("../README.md") as fp:
    long_description = fp.read()

setuptools.setup(
    name="sql-based-etl",
    version="1.0.0",

    description="A CDK Python app for SQL-based ETL",
    long_description=long_description,
    long_description_content_type="text/markdown",
    
    author="meloyang",

    package_dir={"": "./"},
    packages=setuptools.find_packages(where="./"),

    install_requires=[
        "aws-cdk.core==1.82.0",
        "aws-cdk.aws_iam==1.82.0",
        "aws-cdk.aws_eks==1.82.0",
        "aws-cdk.aws_ec2==1.82.0",
        "aws-cdk.aws_s3==1.82.0",
        "aws-cdk.aws_s3_deployment==1.82.0",
        "aws-cdk.aws_codecommit==1.82.0",
        "aws-cdk.aws_codebuild==1.82.0",
        "aws-cdk.aws_codepipeline==1.82.0",
        "aws-cdk.aws_codepipeline_actions==1.82.0",
        "aws_cdk.aws_secretsmanager==1.82.0",
        "aws_cdk.aws_elasticloadbalancingv2==1.82.0",
        "aws-cdk.aws_cloudfront==1.82.0",
        "aws-cdk.aws_cloudfront_origins==1.82.0",
        # "aws-cdk.aws_efs==1.82.0",
        "pyyaml==5.3"
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: MIT License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
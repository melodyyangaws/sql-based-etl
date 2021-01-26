/**
 *  Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
 *  with the License. A copy of the License is located at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
 *  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
 *  and limitations under the License.
 */

// Imports
const fs = require('fs');

// Paths
const global_s3_assets = '../global-s3-assets';

function assetRef(s3BucketRef) {
    // Set the S3 key reference
    let artifactHash = Object.assign(s3BucketRef);
    artifactHash = artifactHash.replace('AssetParameters', '');
    artifactHash = artifactHash.substring(0, artifactHash.indexOf('S3Bucket'));
    const assetPath = `asset${artifactHash}`;

    return assetPath;
};
function clearParameter(template) {
    const parameters = (template.Parameters) ? template.Parameters : {};
    const assetParameters = Object.keys(parameters).filter(function(key) {
      return key.includes('AssetParameters');
    });
    assetParameters.forEach(function(a) {
        template.Parameters[a] = undefined;
    });
};

// For each template in global_s3_assets ...
fs.readdirSync(global_s3_assets).forEach(file => {

    // Import and parse template file
    const raw_template = fs.readFileSync(`${global_s3_assets}/${file}`);
    let template = JSON.parse(raw_template);

    // Clean-up parameters section
    clearParameter(template);

    // Clean-up Lambda function code dependencies
    const resources = (template.Resources) ? template.Resources : {};
    const replaceS3Bucket = Object.keys(resources).filter(function(key) {
      return (resources[key].Type === "AWS::Lambda::Function" || resources[key].Type === "AWS::Lambda::LayerVersion" || resources[key].Type === "Custom::CDKBucketDeployment" || resources[key].Type === "AWS::CloudFormation::Stack");
    });
    replaceS3Bucket.forEach(function(f) {
        const fn = template.Resources[f];
        if (fn.Properties.hasOwnProperty('Code') && fn.Properties.Code.hasOwnProperty('S3Bucket')) {
          assetPath = assetRef(fn.Properties.Code.S3Bucket.Ref);
          // Set Lambda::Function S3 bucket reference
          fn.Properties.Code.S3Key = `%%SOLUTION_NAME%%/%%VERSION%%/${assetPath}.zip`;
          fn.Properties.Code.S3Bucket = {'Fn::Sub': '%%BUCKET_NAME%%'};
          // Set the handler
          const handler = fn.Properties.Handler;
          fn.Properties.Handler = `${assetPath}/${handler}`;
        }
        else if (fn.Properties.hasOwnProperty('Content') && fn.Properties.Content.hasOwnProperty('S3Bucket')) {
          assetPath = assetRef(fn.Properties.Content.S3Bucket.Ref);
          // Set Lambda::LayerVersion S3 bucket reference
          fn.Properties.Content.S3Key = `%%SOLUTION_NAME%%/%%VERSION%%/${assetPath}.zip`;
          fn.Properties.Content.S3Bucket = {'Fn::Sub': '%%BUCKET_NAME%%'};    
        }
        else if (fn.Properties.hasOwnProperty('SourceBucketNames')) {
          assetPath = assetRef(fn.Properties.SourceBucketNames[0].Ref);
          // Set CDKBucketDeployment S3 bucket reference
          fn.Properties.SourceObjectKeys = [`%%SOLUTION_NAME%%/%%VERSION%%/${assetPath}.zip`];
          fn.Properties.SourceBucketNames = [{'Fn::Sub': '%%BUCKET_NAME%%'}];
        }
        else if (fn.Properties.hasOwnProperty('TemplateURL')) {
          arrayKey = Object.keys(fn.Properties.TemplateURL)[0];
          assetPath = fn.Properties.TemplateURL[arrayKey][1].filter(function(key){
            if (key.hasOwnProperty('Ref') && key.Ref.includes('AssetParameters')) 
              return assetRef(key.Ref);
          });
          // Set NestedStack S3 bucket reference
          fn.Properties.TemplateURL = {'Fn::Sub':'https://%%BUCKET_NAME%%.s3.amazonaws.com/%%SOLUTION_NAME%%/%%VERSION%%/${assetPath}.zip'}
          //Clean-up nested stack parameters section
          clearParameter(fn.Properties);
        };
    });

    // Output modified template file
    const output_template = JSON.stringify(template, null, 2);
    fs.writeFileSync(`${global_s3_assets}/${file}`, output_template);
});
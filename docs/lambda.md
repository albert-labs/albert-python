# AWS Lambda layer

Albert publishes a public AWS Lambda layer for each SDK release. Attach it to your function and `import albert` works without bundling the SDK or its dependencies in your deployment package.

## Choosing a layer

One layer exists per Python runtime and architecture. Pick the one that matches your function's configuration:

| Layer name | Runtime | Architecture |
|---|---|---|
| `albert-python-py311-x86_64` | python3.11 | x86_64 |
| `albert-python-py311-arm64` | python3.11 | arm64 |
| `albert-python-py312-x86_64` | python3.12 | x86_64 |
| `albert-python-py312-arm64` | python3.12 | arm64 |
| `albert-python-py313-x86_64` | python3.13 | x86_64 |
| `albert-python-py313-arm64` | python3.13 | arm64 |
| `albert-python-py314-x86_64` | python3.14 | x86_64 |
| `albert-python-py314-arm64` | python3.14 | arm64 |

Layers are currently published in `us-west-2`. Lambda layers are region scoped, so your function must be in the same region as the layer.

Layer ARNs follow this pattern:

```text
arn:aws:lambda:us-west-2:<albert-account-id>:layer:albert-python-py312-x86_64:<layer-version>
```

## Versioning

Each SDK release adds a new version to every layer. The layer version number is assigned by AWS and is not the SDK version, so always check the layer description, which records the SDK version it contains:

```bash
aws lambda get-layer-version-by-arn \
  --arn arn:aws:lambda:us-west-2:<albert-account-id>:layer:albert-python-py312-x86_64:3 \
  --query Description --output text
```

```text
albert-python 1.19.0 | python3.12 | x86_64 | 2026-09-17T14:02:00Z | sha=abc1234
```

The ARNs for each release are listed in the [GitHub release notes](https://github.com/albert-labs/albert-python/releases). Pin your function to a specific layer version ARN and upgrade deliberately, the same way you would pin a package version.

## Attaching the layer

=== "AWS CLI"

    ```bash
    aws lambda update-function-configuration \
      --function-name my-function \
      --layers arn:aws:lambda:us-west-2:<albert-account-id>:layer:albert-python-py312-x86_64:3
    ```

=== "SAM / CloudFormation"

    ```yaml
    MyFunction:
      Type: AWS::Serverless::Function
      Properties:
        Runtime: python3.12
        Architectures: [x86_64]
        Layers:
          - arn:aws:lambda:us-west-2:<albert-account-id>:layer:albert-python-py312-x86_64:3
    ```

=== "Terraform"

    ```hcl
    resource "aws_lambda_function" "my_function" {
      runtime       = "python3.12"
      architectures = ["x86_64"]
      layers        = ["arn:aws:lambda:us-west-2:<albert-account-id>:layer:albert-python-py312-x86_64:3"]
      # ...
    }
    ```

## What the layer contains

The layer installs `albert` and its dependencies (pandas, numpy, pydantic, requests, pyjwt, tenacity) under `python/`, which Lambda adds to `sys.path`. Do not bundle pandas or numpy in your own deployment package as well: duplicate copies waste space and can shadow the versions the SDK was built against.

Credentials work the same way as anywhere else. See [Authentication](authentication.md) for using a client credential token from an environment variable, which is the usual approach in Lambda.

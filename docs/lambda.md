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

## Regions

Lambda layers are region scoped: your function must be in the same region as the layer, or AWS reports a permissions error even though the layer is public. Every release is published to these regions by default:

- `us-west-2` (US West, Oregon)
- `us-east-1` (US East, N. Virginia)
- `eu-central-1` (Europe, Frankfurt)
- `eu-west-1` (Europe, Ireland)

Need the layer in another region? [Open an issue](https://github.com/albert-labs/albert-python/issues/new?title=Lambda%20layer%20region%20request%3A%20) with the region code and we can add it to this list, so it is published there for every release.

## Available layer versions

AWS does not let other accounts browse or search our layers, so every public layer version is listed here. Filter by SDK version, Python runtime, architecture, and your function's region, then copy the ARN:

<div id="lambda-layer-catalog">
<p>Loading layer versions. If this does not load, download <a href="https://docs.developer.albertinvent.com/albert-python/lambda-layers.json">lambda-layers.json</a> directly.</p>
</div>

The same list is published as JSON at [`https://docs.developer.albertinvent.com/albert-python/lambda-layers.json`](https://docs.developer.albertinvent.com/albert-python/lambda-layers.json) for scripts and infrastructure code. Entries are sorted newest SDK version first, so the first match is the latest layer:

```bash
curl -s https://docs.developer.albertinvent.com/albert-python/lambda-layers.json \
  | jq -r '[.layers[] | select(.python == "3.12" and .architecture == "x86_64" and .region == "us-west-2")][0].arn'
```

Each entry includes `sdk_version`, `python`, `architecture`, `region`, `layer_name`, `layer_version`, `arn`, `created`, and `description`.

## Versioning

Each SDK release adds a new version to every layer. The layer version number is assigned by AWS and is not the SDK version. The table above maps one to the other, and each layer's description also records the SDK version it contains:

```bash
aws lambda get-layer-version-by-arn \
  --arn arn:aws:lambda:us-west-2:<albert-account-id>:layer:albert-python-py312-x86_64:3 \
  --query Description --output text
```

```text
albert-python 1.19.0 | python3.12 | x86_64 | 2026-09-17T14:02:00Z | sha=abc1234
```

Every [GitHub release](https://github.com/albert-labs/albert-python/releases) also ends with a **Lambda layers** table listing the layer version ARNs published for that release. Pin your function to a specific layer version ARN and upgrade deliberately, the same way you would pin a package version.

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

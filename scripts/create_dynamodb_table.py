import os
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
DDB_ENDPOINT_URL = os.getenv("DDB_ENDPOINT_URL", "http://localhost:8000")
TELEM_TABLE = os.getenv("DDB_TABLE_NAME", "UGVTelemetry")
LIDAR_TABLE = os.getenv("LIDAR_TABLE_NAME", "UGVLidarScans")


def ensure_table(dynamodb, table_name, key_schema, attribute_definitions, billing_mode="PAY_PER_REQUEST", gsi=None):
    try:
        table = dynamodb.Table(table_name)
        table.load()
        print(f"Table already exists: {table_name}")
        return table
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceNotFoundException":
            raise

    params = {
        "TableName": table_name,
        "KeySchema": key_schema,
        "AttributeDefinitions": attribute_definitions,
        "BillingMode": billing_mode,
    }
    if gsi:
        params["GlobalSecondaryIndexes"] = gsi

    print(f"Creating table {table_name} ...")
    table = dynamodb.create_table(**params)
    table.wait_until_exists()
    print(f"Created: {table_name}")
    return table


def main():
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION, endpoint_url=DDB_ENDPOINT_URL)

    # Telemetry table: device_id (HASH), timestamp (RANGE)
    ensure_table(
        dynamodb,
        TELEM_TABLE,
        key_schema=[
            {"AttributeName": "device_id", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"},
        ],
        attribute_definitions=[
            {"AttributeName": "device_id", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "N"},
        ],
    )

    # LiDAR scans: device_id (HASH), timestamp (RANGE)
    ensure_table(
        dynamodb,
        LIDAR_TABLE,
        key_schema=[
            {"AttributeName": "device_id", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"},
        ],
        attribute_definitions=[
            {"AttributeName": "device_id", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "N"},
        ],
    )


if __name__ == "__main__":
    main() 
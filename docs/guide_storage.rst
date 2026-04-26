Storage Configuration: Local & Cloud
====================================

This guide explains how to configure where your performance data is stored, supporting both local filesystem and AWS S3.

Overview
--------

Performance databases can grow large and shouldn't be stored in the versioned package directory. The library provides a pluggable storage abstraction supporting:

- **Local filesystem** - Single machine, development, testing
- **AWS S3** - Cloud, team collaboration, scalable deployments

You configure storage once, and all importers/tools use it automatically.

Local Filesystem Storage
------------------------

Default Configuration
^^^^^^^^^^^^^^^^^^^^^

By default, data is stored in your home directory:

.. code-block:: python

    from athletics_performance.importers import AthleFrImporter

    importer = AthleFrImporter()  # Uses ~/.athletics_performance/data/

This works out of the box with no configuration needed.

Custom Local Path
^^^^^^^^^^^^^^^^^

Specify a different local directory:

.. code-block:: python

    from athletics_performance.importers import AthleFrImporter
    from athletics_performance.storage import LocalDataStore

    # Explicit path
    store = LocalDataStore('/data/athletics')
    importer = AthleFrImporter(data_store=store)

    # Or via environment variable
    import os
    os.environ['ATHLETICS_STORAGE_PATH'] = '/var/lib/athletics-performance'

Best Practices for Local Storage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Development**: ``~/athletics-data`` or ``./data/``
- **Single server**: ``/var/lib/athletics-performance``
- **Shared server**: ``/mnt/shared-storage/athletics``
- **Temporary**: ``/tmp/athletics-test`` (for tests only)

AWS S3 Storage
--------------

Prerequisites
^^^^^^^^^^^^^

Install S3 support:

.. code-block:: bash

    pip install athletics_performance[s3]

Configure AWS credentials (one of):

1. **Environment variables**:

   .. code-block:: bash

       export AWS_ACCESS_KEY_ID=your-key-id
       export AWS_SECRET_ACCESS_KEY=your-secret-key
       export AWS_DEFAULT_REGION=eu-west-1

2. **AWS credentials file** (``~/.aws/credentials``):

   .. code-block:: ini

       [default]
       aws_access_key_id = your-key-id
       aws_secret_access_key = your-secret-key

3. **IAM Role** (on EC2, ECS, Lambda):

   Attach an IAM role with S3 permissions

Basic S3 Configuration
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from athletics_performance.importers import AthleFrImporter
    from athletics_performance.storage import S3DataStore

    # Create S3 storage
    store = S3DataStore(
        bucket='my-athletics-bucket',
        prefix='performances',  # Subdirectory in bucket
        region_name='eu-west-1'
    )

    importer = AthleFrImporter(data_store=store)

    # Use normally
    importer.import_to_parquet(club_id="069106", season=2026)

S3 Bucket Structure
^^^^^^^^^^^^^^^^^^^

Data is organized as:

.. code-block:: text

    my-athletics-bucket/
    └── performances/
        ├── bronze/
        │   └── ac_lyon_2026.parquet
        ├── silver/
        │   └── ac_lyon_2026_processed.parquet
        └── gold/
            └── ac_lyon_records.parquet

Configuration via Environment Variables
----------------------------------------

Define storage using environment variables for DevOps/containerization:

Local Storage
^^^^^^^^^^^^^

.. code-block:: bash

    export ATHLETICS_STORAGE_TYPE=local
    export ATHLETICS_STORAGE_PATH=/data/athletics

S3 Storage
^^^^^^^^^^

.. code-block:: bash

    export ATHLETICS_STORAGE_TYPE=s3
    export ATHLETICS_S3_BUCKET=my-athletics-bucket
    export ATHLETICS_S3_PREFIX=performances
    export ATHLETICS_AWS_REGION=eu-west-1

Then use without explicit configuration:

.. code-block:: python

    from athletics_performance.importers import AthleFrImporter

    importer = AthleFrImporter()  # Reads from env vars
    importer.import_to_parquet(club_id="069106")

Dynamic Configuration
---------------------

Choose storage at runtime:

.. code-block:: python

    from athletics_performance.storage import get_default_data_store
    from athletics_performance.importers import AthleFrImporter

    # Build config based on environment
    if os.environ.get('ENVIRONMENT') == 'production':
        config = {
            'type': 's3',
            'bucket': 'prod-athletics-data',
            'prefix': 'performances',
            'region': 'eu-west-1'
        }
    else:
        config = {
            'type': 'local',
            'path': '/tmp/athletics-test'
        }

    store = get_default_data_store(config)
    importer = AthleFrImporter(data_store=store)

Configuration File
^^^^^^^^^^^^^^^^^^

Store configuration in YAML/JSON:

.. code-block:: yaml

    # config.yaml
    storage:
      type: s3
      bucket: my-athletics-bucket
      prefix: performances
      region: eu-west-1

Load it:

.. code-block:: python

    import yaml
    from athletics_performance.storage import get_default_data_store

    with open('config.yaml') as f:
        config = yaml.safe_load(f)

    store = get_default_data_store(config['storage'])

Migrating Between Backends
---------------------------

Move data from local to S3:

.. code-block:: python

    from athletics_performance.storage import LocalDataStore, S3DataStore
    from athletics_performance.importers import AthleFrImporter
    import pandas as pd

    # Read from local
    local_store = LocalDataStore('/data/athletics')
    local_importer = AthleFrImporter(data_store=local_store)

    # Write to S3
    s3_store = S3DataStore('new-bucket', 'performances')
    s3_importer = AthleFrImporter(data_store=s3_store)

    # Copy all files
    for filename in local_store.list_files('.'):
        df = local_importer.load_from_parquet(filename)
        s3_importer.data_store.write_parquet(df, filename)

Docker & Kubernetes Deployment
-------------------------------

Docker Compose Example
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    # docker-compose.yml
    version: '3'
    services:
      app:
        image: my-athletics-app
        environment:
          - ATHLETICS_STORAGE_TYPE=s3
          - ATHLETICS_S3_BUCKET=org-bucket
          - ATHLETICS_S3_PREFIX=athletics
          - AWS_ACCESS_KEY_ID=${AWS_KEY}
          - AWS_SECRET_ACCESS_KEY=${AWS_SECRET}
        volumes:
          - /var/lib/athletics:/var/lib/data  # Local cache

Kubernetes Example
^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

    # deployment.yaml
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: athletics-app
    spec:
      containers:
      - name: app
        image: my-athletics-app
        env:
        - name: ATHLETICS_STORAGE_TYPE
          value: "s3"
        - name: ATHLETICS_S3_BUCKET
          valueFrom:
            configMapKeyRef:
              name: athletics-config
              key: bucket
        - name: AWS_ACCESS_KEY_ID
          valueFrom:
            secretKeyRef:
              name: aws-credentials
              key: access-key
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: aws-credentials
              key: secret-key

Storage Comparison
------------------

.. list-table::
   :header-rows: 1

   * - Feature
     - Local FS
     - S3
   * - Setup Time
     - Immediate
     - 5-10 minutes
   * - Cost
     - Free
     - Pay per GB/request
   * - Scalability
     - Limited (single disk)
     - Unlimited
   * - Sharing
     - NFS/SMB needed
     - Built-in (IAM)
   * - Backup
     - Manual
     - Built-in
   * - Multi-region
     - No
     - Yes
   * - Compliance
     - Depends on location
     - Configurable

Performance Considerations
--------------------------

**Local Storage**
- Fast local disk access
- Limited by single machine's I/O
- Good for <100GB datasets

**S3 Storage**
- Network latency (~100ms per request)
- Excellent parallelization
- Good for team collaboration and scaling
- Enable S3 Transfer Acceleration for faster uploads

.. code-block:: python

    from athletics_performance.storage import S3DataStore

    store = S3DataStore(
        bucket='my-bucket',
        prefix='performances',
        # Enable transfer acceleration
        # (requires S3 bucket configuration)
    )

Best Practices
--------------

1. **Use environment variables** - Don't hardcode paths/credentials
2. **Test locally first** - Develop with LocalDataStore, deploy with S3
3. **Organize with medallion** - Use bronze/silver/gold folders
4. **Archive old data** - Move old bronze/silver to S3 Glacier
5. **Monitor usage** - Track S3 requests and storage costs
6. **Version configurations** - Store config files in git (not secrets)
7. **Use IAM roles** - Never use root AWS credentials

AWS Cost Optimization
---------------------

.. code-block:: python

    # Put frequently-accessed data in standard S3
    # Archive old data to Glacier
    import boto3
    from datetime import datetime, timedelta

    s3 = boto3.client('s3')

    # Transition old objects to Glacier
    lifecycle_policy = {
        'Rules': [
            {
                'Id': 'archive-old-bronze',
                'Filter': {'Prefix': 'performances/bronze/'},
                'Transitions': [
                    {
                        'Days': 90,
                        'StorageClass': 'GLACIER'
                    }
                ],
                'Status': 'Enabled'
            }
        ]
    }

    s3.put_bucket_lifecycle_configuration(
        Bucket='my-bucket',
        LifecycleConfiguration=lifecycle_policy
    )

See Also
--------

- :doc:`guide_data_ingestion` - How to import performances
- :doc:`guide_medallion` - Data layer architecture
- `AWS S3 Documentation <https://docs.aws.amazon.com/s3/>`_
- `AWS IAM Best Practices <https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html>`_

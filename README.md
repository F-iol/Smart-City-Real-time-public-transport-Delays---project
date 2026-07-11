## Current outlook
```mermaid
graph TB

classDef success fill:#d4edda,stroke:#28a745,stroke-width:2px,color:#155724;
classDef tech fill:#e2e3e5,stroke:#383d41,stroke-width:1px,color:#383d41;


%% ---------- TECHNOLOGY STACK ----------
subgraph Tools["Technologies"]
    direction LR

    T1[Python]
    T2[PySpark<br>Apache Spark 3.5]
    T3[Terraform]
    T4[AWS Glue 5.0]

    T1 --- T2 --- T3 --- T4
end

class T1,T2,T3,T4 tech;


%% ---------- PIPELINE ----------
subgraph Pipeline["Data Pipeline"]
    direction LR

    subgraph Bronze["Etap 1: Ingestion & Bronze Layer"]
        A[Warsaw Public Transport API]
        B["S3 Bronze<br>smart-city-bronze-fiol"]

        A -->|fetch_to_s3.py| B
    end


    subgraph Silver["Etap 2: Silver Layer"]
        C{{"AWS Glue Job<br>bronze_to_silver.py"}}
        D["S3 Silver<br>Parquet + partitions"]
        E["Glue Crawler"]
        F[("Glue Data Catalog<br>Database + Tables")]
        G[["Amazon Athena<br>SQL Analytics"]]

        C -->|Parquet| D
        D --> E
        E --> F
        F --> G
    end


    B --> C

end


%% invisible positioning link
Tools ~~~ Pipeline


class A,B,C,D,E,F,G success;
```


## AWS Lambda problem

Planned on using AWS lambda for ingestion process , I set it up but AWS was unable to retrieve any data from the Warsaw's API due to repeated timeouts <br>
Issue appears to be related to inaccessible API while using AWS enviroment possibly due to Warsaw's API filtering.  
Since it worked locally I switched to more suitable approach to ingest data and upload it to S3 manually via ```ingestion.py```
